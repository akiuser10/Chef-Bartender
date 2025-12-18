"""
Knowledge Hub Blueprint
Handles Bartender Library and Chef Library pages
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from functools import wraps
from models import Book, db
from utils.helpers import get_organization_filter
from utils.file_upload import save_uploaded_file, allowed_file
import os
from werkzeug.utils import secure_filename
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
from PIL import Image
import uuid
from io import BytesIO

knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/knowledge')


def fetch_cover_image_from_url(article_url):
    """
    Fetch cover image from a website URL using Open Graph tags or meta tags.
    Downloads and saves the image to uploads/books/covers/ for future use.
    Returns the path to the saved image, or None if extraction fails.
    """
    try:
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch the webpage
        response = requests.get(article_url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find Open Graph image first (og:image)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image.get('content')
        else:
            # Try Twitter Card image (twitter:image)
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                image_url = twitter_image.get('content')
            else:
                # Try to find the largest image on the page
                images = soup.find_all('img')
                if not images:
                    return None
                
                # Get the largest image (by dimensions or file size)
                largest_image = None
                max_size = 0
                
                for img in images:
                    src = img.get('src') or img.get('data-src')
                    if not src:
                        continue
                    
                    # Make absolute URL
                    if not src.startswith('http'):
                        src = urljoin(article_url, src)
                    
                    # Try to get image dimensions
                    width = int(img.get('width', 0) or 0)
                    height = int(img.get('height', 0) or 0)
                    size = width * height
                    
                    if size > max_size:
                        max_size = size
                        largest_image = src
                
                if not largest_image:
                    return None
                
                image_url = largest_image
        
        # Make absolute URL if relative
        if not image_url.startswith('http'):
            image_url = urljoin(article_url, image_url)
        
        # Download the image
        img_response = requests.get(image_url, headers=headers, timeout=10, stream=True)
        img_response.raise_for_status()
        
        # Open image with PIL
        img = Image.open(BytesIO(img_response.content))
        
        # Convert to RGB if necessary (handles RGBA, P, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize to reasonable cover size (maintain aspect ratio)
        max_width = 600
        max_height = 800
        
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Generate unique filename
        filename = f"{uuid.uuid4().hex}.jpg"
        
        # Ensure output directory exists
        upload_folder = current_app.config['UPLOAD_FOLDER']
        output_dir = os.path.join(upload_folder, 'books', 'covers')
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the image
        output_path = os.path.join(output_dir, filename)
        img.save(output_path, 'JPEG', quality=85)
        
        # Return the relative path with 'uploads/' prefix
        return os.path.join('uploads', 'books', 'covers', filename).replace('\\', '/')
        
    except Exception as e:
        current_app.logger.error(f'Error fetching cover image from URL {article_url}: {str(e)}', exc_info=True)
        return None


def extract_pdf_first_page_as_image(pdf_path, output_folder='books/covers'):
    """
    Extract the first page of a PDF and save it as an image.
    Returns the path to the saved image, or None if extraction fails.
    """
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        import uuid
        
        # Open the PDF
        pdf_document = fitz.open(pdf_path)
        
        if len(pdf_document) == 0:
            pdf_document.close()
            return None
        
        # Get the first page
        first_page = pdf_document[0]
        
        # Render page to an image (pixmap)
        # Use a reasonable resolution (2x for better quality)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = first_page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Resize to a reasonable cover size (e.g., 400x600 for portrait, 600x400 for landscape)
        # Maintain aspect ratio
        max_width = 600
        max_height = 800
        
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Generate a unique filename
        filename = f"{uuid.uuid4().hex}.jpg"
        
        # Ensure output directory exists
        upload_folder = current_app.config['UPLOAD_FOLDER']
        output_dir = os.path.join(upload_folder, output_folder)
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the image
        output_path = os.path.join(output_dir, filename)
        img.save(output_path, 'JPEG', quality=85)
        
        # Clean up
        pix = None
        pdf_document.close()
        
        # Return the relative path with 'uploads/' prefix (as stored in database, matching save_uploaded_file format)
        return os.path.join('uploads', output_folder, filename).replace('\\', '/')
        
    except Exception as e:
        current_app.logger.error(f'Error extracting PDF first page: {str(e)}', exc_info=True)
        return None


def role_required(*roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                from flask import redirect, url_for
                return redirect(url_for('auth.login'))
            if current_user.user_role not in roles:
                from flask import abort
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@knowledge_bp.route('/bartender-library')
@login_required
@role_required('Bartender', 'Manager')
def bartender_library():
    """Display Bartender Library page - Only visible to Manager and Bartender"""
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    org_filter = get_organization_filter(Book)
    books = Book.query.filter(org_filter).filter_by(library_type='bartender').order_by(Book.created_at.desc()).all()
    return render_template('knowledge/bartender_library.html', books=books)


@knowledge_bp.route('/chef-library')
@login_required
@role_required('Chef', 'Manager')
def chef_library():
    """Display Chef Library page - Only visible to Manager and Chef"""
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    org_filter = get_organization_filter(Book)
    books = Book.query.filter(org_filter).filter_by(library_type='chef').order_by(Book.created_at.desc()).all()
    return render_template('knowledge/chef_library.html', books=books)


@knowledge_bp.route('/add-book', methods=['POST'])
@login_required
@role_required('Manager')
def add_book():
    """Add a new article link to the library"""
    from utils.db_helpers import ensure_schema_updates
    from urllib.parse import urlparse
    ensure_schema_updates()
    
    try:
        title = request.form.get('title', '').strip()
        article_url = request.form.get('article_url', '').strip()
        library_type = request.form.get('library_type', '').strip()
        
        if not library_type:
            flash('Library type is required.', 'error')
            return redirect(url_for('knowledge.bartender_library'))
        
        if library_type not in ['bartender', 'chef']:
            flash('Invalid library type.', 'error')
            return redirect(url_for('knowledge.bartender_library'))
        
        # Validate URL
        if not article_url:
            flash('Article URL is required.', 'error')
            return redirect(url_for(f'knowledge.{library_type}_library'))
        
        # Validate URL format
        try:
            parsed = urlparse(article_url)
            if not parsed.scheme or not parsed.netloc:
                flash('Please enter a valid URL (e.g., https://example.com/article).', 'error')
                return redirect(url_for(f'knowledge.{library_type}_library'))
        except Exception:
            flash('Please enter a valid URL.', 'error')
            return redirect(url_for(f'knowledge.{library_type}_library'))
        
        # If no title provided, use a default
        if not title:
            title = 'Article Link'
        
        # Handle cover image upload (optional)
        cover_image_path = None
        cover_file = request.files.get('cover_image')
        if cover_file and cover_file.filename != '':
            if allowed_file(cover_file.filename):
                cover_image_path = save_uploaded_file(cover_file, 'books/covers')
        else:
            # If no manual upload, try to fetch cover image from article URL
            cover_image_path = fetch_cover_image_from_url(article_url)
        
        # Ensure organization is set (required for persistence and filtering)
        organisation = current_user.organisation.strip() if current_user.organisation and current_user.organisation.strip() else None
        if not organisation:
            current_app.logger.warning(f'User {current_user.id} has no organisation set, using None')
        
        # Create book record with article URL
        book = Book(
            title=title,
            author=None,
            library_type=library_type,
            article_url=article_url,
            pdf_path=None,  # No PDF for article links
            cover_image_path=cover_image_path,  # Optional cover image (from upload or auto-fetch)
            created_by=current_user.id,
            organisation=organisation
        )
        
        db.session.add(book)
        
        # Commit to database
        try:
            db.session.commit()
            db.session.refresh(book)
            if book.is_persisted():
                current_app.logger.info(f'Article "{title}" (ID: {book.id}) successfully saved to database for organization: {organisation}')
                flash('Article link added successfully!', 'success')
            else:
                current_app.logger.error(f'Article "{title}" was not properly persisted after commit')
                flash('Warning: Article may not have been saved correctly. Please verify.', 'warning')
        except Exception as commit_error:
            db.session.rollback()
            current_app.logger.error(f'Database commit failed for article "{title}": {str(commit_error)}', exc_info=True)
            flash('Error: Article could not be saved to database. Please try again.', 'error')
            return redirect(url_for(f'knowledge.{library_type}_library'))
        
        return redirect(url_for(f'knowledge.{library_type}_library'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error adding article: {str(e)}', exc_info=True)
        flash(f'Error adding article: {str(e)}', 'error')
        return redirect(url_for('knowledge.bartender_library'))


@knowledge_bp.route('/book/<int:book_id>/pdf')
@login_required
def view_book_pdf(book_id):
    """Serve PDF file for a book - Access restricted by library type and user role"""
    from utils.db_helpers import ensure_schema_updates
    from werkzeug.exceptions import NotFound
    from flask import abort
    ensure_schema_updates()
    
    try:
        org_filter = get_organization_filter(Book)
        book = Book.query.filter(org_filter).filter_by(id=book_id).first()
        
        if not book:
            current_app.logger.error(f'Book with id {book_id} not found for user {current_user.id}')
            raise NotFound(description=f'Book with id {book_id} not found')
        
        # Check if user has access to this library type
        if book.library_type == 'bartender' and current_user.user_role not in ['Bartender', 'Manager']:
            abort(403)
        elif book.library_type == 'chef' and current_user.user_role not in ['Chef', 'Manager']:
            abort(403)
        
        if not book.pdf_path:
            current_app.logger.error(f'Book {book_id} has no pdf_path')
            flash('PDF file not found.', 'error')
            # Redirect to the correct library based on book type
            library_route = f'{book.library_type}_library' if book.library_type in ['bartender', 'chef'] else 'bartender_library'
            return redirect(url_for(f'knowledge.{library_route}'))
        
        # book.pdf_path is stored as 'uploads/books/pdfs/filename.pdf' (from save_uploaded_file)
        # We need to remove 'uploads/' prefix to get the relative path for send_from_directory
        stored_path = book.pdf_path
        
        # Normalize the path - remove 'uploads/' prefix if present
        if stored_path.startswith('uploads/'):
            file_path = stored_path.replace('uploads/', '', 1)
        else:
            file_path = stored_path
        
        # Construct full path to verify file exists
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path)
        
        # Check if file exists at the expected location
        if not os.path.exists(full_path):
            # Try alternative path formats
            alt_paths = [
                # Try with uploads/ prefix as absolute path
                os.path.join(current_app.config['UPLOAD_FOLDER'], stored_path),
                # Try the stored path as-is (if it's already absolute)
                stored_path,
                # Try without uploads/ prefix
                os.path.join(current_app.config['UPLOAD_FOLDER'], file_path),
            ]
            
            found = False
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    # Determine the correct file_path for send_from_directory
                    if alt_path.startswith(current_app.config['UPLOAD_FOLDER']):
                        # Extract relative path from UPLOAD_FOLDER
                        file_path = os.path.relpath(alt_path, current_app.config['UPLOAD_FOLDER'])
                    elif alt_path.startswith('uploads/'):
                        # Remove uploads/ prefix
                        file_path = alt_path.replace('uploads/', '', 1)
                    else:
                        # Use as-is
                        file_path = alt_path
                    found = True
                    current_app.logger.info(f'Found PDF at alternative path: {alt_path}, using file_path: {file_path}')
                    break
            
            if not found:
                # Log detailed error information
                current_app.logger.error(
                    f'PDF file not found for book {book_id}. '
                    f'Stored path: {stored_path}, '
                    f'Expected full path: {full_path}, '
                    f'UPLOAD_FOLDER: {current_app.config["UPLOAD_FOLDER"]}, '
                    f'File exists check: {os.path.exists(full_path)}'
                )
                flash('PDF file not found on server.', 'error')
                # Redirect to the correct library based on book type
                library_route = f'{book.library_type}_library' if book.library_type in ['bartender', 'chef'] else 'bartender_library'
                return redirect(url_for(f'knowledge.{library_route}'))
        
        # Use send_from_directory to serve the file directly
        # file_path should be relative to UPLOAD_FOLDER (e.g., 'books/pdfs/filename.pdf')
        try:
            current_app.logger.info(f'Serving PDF for book {book_id}: {file_path} from {current_app.config["UPLOAD_FOLDER"]}')
            return send_from_directory(
                current_app.config['UPLOAD_FOLDER'],
                file_path,
                as_attachment=False,
                mimetype='application/pdf'
            )
        except Exception as e:
            current_app.logger.error(f'Error serving PDF file: {str(e)}, file_path: {file_path}, UPLOAD_FOLDER: {current_app.config["UPLOAD_FOLDER"]}')
            flash('Error loading PDF file.', 'error')
            library_route = f'{book.library_type}_library' if book.library_type in ['bartender', 'chef'] else 'bartender_library'
            return redirect(url_for(f'knowledge.{library_route}'))
    except NotFound:
        raise
    except Exception as e:
        current_app.logger.error(f'Error serving PDF for book {book_id}: {str(e)}', exc_info=True)
        flash('Error loading PDF file.', 'error')
        # Try to get the book to determine which library to redirect to
        try:
            org_filter = get_organization_filter(Book)
            book = Book.query.filter(org_filter).filter_by(id=book_id).first()
            if book and book.library_type in ['bartender', 'chef']:
                library_route = f'{book.library_type}_library'
            else:
                library_route = 'bartender_library'
        except:
            library_route = 'bartender_library'
        return redirect(url_for(f'knowledge.{library_route}'))


@knowledge_bp.route('/book/<int:book_id>/edit', methods=['POST'])
@login_required
@role_required('Manager')
def edit_book(book_id):
    """Edit an article link"""
    from utils.db_helpers import ensure_schema_updates
    from urllib.parse import urlparse
    ensure_schema_updates()
    
    try:
        org_filter = get_organization_filter(Book)
        book = Book.query.filter(org_filter).filter_by(id=book_id).first_or_404()
        
        title = request.form.get('title', '').strip()
        article_url = request.form.get('article_url', '').strip()
        
        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for(f'knowledge.{book.library_type}_library'))
        
        if not article_url:
            flash('Article URL is required.', 'error')
            return redirect(url_for(f'knowledge.{book.library_type}_library'))
        
        # Validate URL format
        try:
            parsed = urlparse(article_url)
            if not parsed.scheme or not parsed.netloc:
                flash('Please enter a valid URL (e.g., https://example.com/article).', 'error')
                return redirect(url_for(f'knowledge.{book.library_type}_library'))
        except Exception:
            flash('Please enter a valid URL.', 'error')
            return redirect(url_for(f'knowledge.{book.library_type}_library'))
        
        # Update book details
        book.title = title
        old_article_url = book.article_url
        book.article_url = article_url
        
        # Handle cover image upload (optional)
        cover_file = request.files.get('cover_image')
        if cover_file and cover_file.filename != '':
            if allowed_file(cover_file.filename):
                # Delete old cover image if exists
                if book.cover_image_path:
                    old_cover_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover_image_path.replace('uploads/', '', 1))
                    try:
                        if os.path.exists(old_cover_path):
                            os.remove(old_cover_path)
                    except Exception as e:
                        current_app.logger.warning(f'Could not delete old cover: {str(e)}')
                
                # Save new cover image
                cover_image_path = save_uploaded_file(cover_file, 'books/covers')
                if cover_image_path:
                    book.cover_image_path = cover_image_path
        elif article_url != old_article_url:
            # If article URL changed and no new cover uploaded, try to fetch new cover
            # Delete old cover image if exists
            if book.cover_image_path:
                old_cover_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover_image_path.replace('uploads/', '', 1))
                try:
                    if os.path.exists(old_cover_path):
                        os.remove(old_cover_path)
                except Exception as e:
                    current_app.logger.warning(f'Could not delete old cover: {str(e)}')
            
            # Fetch new cover image from updated URL
            cover_image_path = fetch_cover_image_from_url(article_url)
            if cover_image_path:
                book.cover_image_path = cover_image_path
        
        db.session.commit()
        
        flash('Article link updated successfully!', 'success')
        return redirect(url_for(f'knowledge.{book.library_type}_library'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error editing article: {str(e)}', exc_info=True)
        flash(f'Error editing article: {str(e)}', 'error')
        return redirect(url_for('knowledge.bartender_library'))


@knowledge_bp.route('/book/<int:book_id>/delete', methods=['POST'])
@login_required
@role_required('Manager')
def delete_book(book_id):
    """Delete a book"""
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    try:
        org_filter = get_organization_filter(Book)
        book = Book.query.filter(org_filter).filter_by(id=book_id).first_or_404()
        
        library_type = book.library_type
        
        # Delete PDF file
        if book.pdf_path:
            pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.pdf_path.replace('uploads/', '', 1))
            try:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            except Exception as e:
                current_app.logger.warning(f'Could not delete PDF file: {str(e)}')
        
        # Delete cover image
        if book.cover_image_path:
            cover_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover_image_path.replace('uploads/', '', 1))
            try:
                if os.path.exists(cover_path):
                    os.remove(cover_path)
            except Exception as e:
                current_app.logger.warning(f'Could not delete cover image: {str(e)}')
        
        # Delete book record - only Managers can delete books
        book_title = book.title  # Store for logging
        book_org = book.organisation  # Store for logging
        
        db.session.delete(book)
        
        try:
            db.session.commit()
            current_app.logger.info(f'Book "{book_title}" (ID: {book_id}) deleted by Manager {current_user.id} from organization: {book_org}')
            flash('Book deleted successfully!', 'success')
        except Exception as commit_error:
            db.session.rollback()
            current_app.logger.error(f'Database commit failed when deleting book {book_id}: {str(commit_error)}', exc_info=True)
            flash('Error: Book could not be deleted from database. Please try again.', 'error')
        
        return redirect(url_for(f'knowledge.{library_type}_library'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting book: {str(e)}', exc_info=True)
        flash(f'Error deleting book: {str(e)}', 'error')
        return redirect(url_for('knowledge.bartender_library'))


@knowledge_bp.route('/book/<int:book_id>/regenerate-cover', methods=['POST'])
@login_required
@role_required('Manager')
def regenerate_cover(book_id):
    """Regenerate cover image from PDF for a book"""
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    try:
        org_filter = get_organization_filter(Book)
        book = Book.query.filter(org_filter).filter_by(id=book_id).first_or_404()
        
        if not book.pdf_path:
            flash('PDF file not found. Cannot regenerate cover.', 'error')
            return redirect(url_for(f'knowledge.{book.library_type}_library'))
        
        # Get PDF full path
        pdf_path_stored = book.pdf_path
        if pdf_path_stored.startswith('uploads/'):
            pdf_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_path_stored.replace('uploads/', '', 1))
        else:
            pdf_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_path_stored)
        
        # Try alternative paths if not found
        if not os.path.exists(pdf_full_path):
            alt_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_path_stored)
            if os.path.exists(alt_path):
                pdf_full_path = alt_path
            else:
                flash('PDF file not found. Cannot regenerate cover.', 'error')
                return redirect(url_for(f'knowledge.{book.library_type}_library'))
        
        # Delete old cover if exists
        if book.cover_image_path:
            old_cover_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover_image_path.replace('uploads/', '', 1))
            try:
                if os.path.exists(old_cover_path):
                    os.remove(old_cover_path)
            except Exception as e:
                current_app.logger.warning(f'Could not delete old cover: {str(e)}')
        
        # Extract new cover from PDF
        cover_image_path = extract_pdf_first_page_as_image(pdf_full_path)
        if cover_image_path:
            book.cover_image_path = cover_image_path
            db.session.commit()
            flash('Cover image regenerated successfully!', 'success')
        else:
            flash('Failed to regenerate cover image from PDF.', 'error')
        
        return redirect(url_for(f'knowledge.{book.library_type}_library'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error regenerating cover: {str(e)}', exc_info=True)
        flash(f'Error regenerating cover: {str(e)}', 'error')
        return redirect(url_for('knowledge.bartender_library'))

