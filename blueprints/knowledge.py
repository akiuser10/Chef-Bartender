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

knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/knowledge')


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
@role_required('Chef', 'Bartender', 'Manager')
def bartender_library():
    """Display Bartender Library page"""
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    org_filter = get_organization_filter(Book)
    books = Book.query.filter(org_filter).filter_by(library_type='bartender').order_by(Book.created_at.desc()).all()
    return render_template('knowledge/bartender_library.html', books=books)


@knowledge_bp.route('/chef-library')
@login_required
@role_required('Chef', 'Bartender', 'Manager')
def chef_library():
    """Display Chef Library page"""
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    org_filter = get_organization_filter(Book)
    books = Book.query.filter(org_filter).filter_by(library_type='chef').order_by(Book.created_at.desc()).all()
    return render_template('knowledge/chef_library.html', books=books)


@knowledge_bp.route('/add-book', methods=['POST'])
@login_required
@role_required('Manager')
def add_book():
    """Add a new book to the library"""
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    try:
        title = request.form.get('title', '').strip()
        library_type = request.form.get('library_type', '').strip()
        
        if not library_type:
            flash('Library type is required.', 'error')
            return redirect(url_for('knowledge.bartender_library'))
        
        if library_type not in ['bartender', 'chef']:
            flash('Invalid library type.', 'error')
            return redirect(url_for('knowledge.bartender_library'))
        
        # Handle PDF upload
        pdf_file = request.files.get('pdf_file')
        if not pdf_file or pdf_file.filename == '':
            flash('PDF file is required.', 'error')
            return redirect(url_for(f'knowledge.{library_type}_library'))
        
        if not allowed_file(pdf_file.filename) or not pdf_file.filename.lower().endswith('.pdf'):
            flash('Only PDF files are allowed.', 'error')
            return redirect(url_for(f'knowledge.{library_type}_library'))
        
        # If no title provided, extract first 3 words from PDF filename
        if not title:
            # Get the original filename without extension
            pdf_filename = secure_filename(pdf_file.filename)
            filename_without_ext = os.path.splitext(pdf_filename)[0]
            # Remove timestamp prefix if present (format: YYYYMMDD_HHMMSS_filename.pdf)
            # Split by underscore and check if first part is a timestamp
            parts = filename_without_ext.split('_')
            if len(parts) > 2 and len(parts[0]) == 8 and len(parts[1]) == 6:
                # Likely a timestamp prefix, use the rest
                filename_without_ext = '_'.join(parts[2:])
            # Extract first 3 words
            words = filename_without_ext.replace('_', ' ').replace('-', ' ').split()
            title = ' '.join(words[:3]) if words else filename_without_ext[:50]  # Fallback to first 50 chars if no words
            if not title:
                title = 'Untitled Book'
        
        # Save PDF
        pdf_path = save_uploaded_file(pdf_file, 'books/pdfs')
        if not pdf_path:
            flash('Error uploading PDF file.', 'error')
            return redirect(url_for(f'knowledge.{library_type}_library'))
        
        # Handle cover image upload (optional)
        cover_image_path = None
        cover_file = request.files.get('cover_image')
        if cover_file and cover_file.filename != '':
            if allowed_file(cover_file.filename):
                cover_image_path = save_uploaded_file(cover_file, 'books/covers')
        
        # If no cover image was uploaded, extract first page of PDF as cover
        if not cover_image_path:
            # pdf_path already includes 'uploads/' prefix from save_uploaded_file
            pdf_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_path.replace('uploads/', '', 1))
            if os.path.exists(pdf_full_path):
                cover_image_path = extract_pdf_first_page_as_image(pdf_full_path)
                if not cover_image_path:
                    current_app.logger.warning(f'Failed to extract cover image from PDF: {pdf_path}')
        
        # Ensure cover_image_path is set (even if None, it will be stored in DB)
        # Create book record
        book = Book(
            title=title,
            author=None,  # Author field removed
            library_type=library_type,
            pdf_path=pdf_path,
            cover_image_path=cover_image_path,  # Can be None if extraction failed
            created_by=current_user.id,
            organisation=current_user.organisation
        )
        
        db.session.add(book)
        db.session.flush()  # Flush to get book.id if needed
        
        # Verify files exist before committing
        if pdf_path:
            pdf_check_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_path.replace('uploads/', '', 1))
            if not os.path.exists(pdf_check_path):
                db.session.rollback()
                flash('Error: PDF file was not saved correctly.', 'error')
                return redirect(url_for(f'knowledge.{library_type}_library'))
        
        if cover_image_path:
            cover_check_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cover_image_path.replace('uploads/', '', 1))
            if not os.path.exists(cover_check_path):
                current_app.logger.warning(f'Cover image file not found at: {cover_check_path}, but continuing...')
                # Don't fail if cover is missing, just log it
        
        db.session.commit()
        
        flash('Book added successfully!', 'success')
        return redirect(url_for(f'knowledge.{library_type}_library'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error adding book: {str(e)}', exc_info=True)
        flash(f'Error adding book: {str(e)}', 'error')
        return redirect(url_for('knowledge.bartender_library'))


@knowledge_bp.route('/book/<int:book_id>/pdf')
@login_required
@role_required('Chef', 'Bartender', 'Manager')
def view_book_pdf(book_id):
    """Serve PDF file for a book"""
    from utils.db_helpers import ensure_schema_updates
    from werkzeug.exceptions import NotFound
    ensure_schema_updates()
    
    try:
        org_filter = get_organization_filter(Book)
        book = Book.query.filter(org_filter).filter_by(id=book_id).first()
        
        if not book:
            current_app.logger.error(f'Book with id {book_id} not found for user {current_user.id}')
            raise NotFound(description=f'Book with id {book_id} not found')
        
        if not book.pdf_path:
            current_app.logger.error(f'Book {book_id} has no pdf_path')
            flash('PDF file not found.', 'error')
            # Redirect to the correct library based on book type
            library_route = f'{book.library_type}_library' if book.library_type in ['bartender', 'chef'] else 'bartender_library'
            return redirect(url_for(f'knowledge.{library_route}'))
        
        # book.pdf_path is stored as 'uploads/books/pdfs/filename.pdf'
        # Remove 'uploads/' prefix to get the relative path
        if book.pdf_path.startswith('uploads/'):
            file_path = book.pdf_path.replace('uploads/', '', 1)
        else:
            file_path = book.pdf_path
        
        # Construct full path to check if file exists
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path)
        
        if not os.path.exists(full_path):
            # Try alternative path formats
            alt_paths = [
                book.pdf_path,  # Try with uploads/ prefix
                os.path.join(current_app.config['UPLOAD_FOLDER'], book.pdf_path),  # Full path with uploads/
            ]
            
            found = False
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    # Update file_path to match found path
                    if alt_path.startswith(current_app.config['UPLOAD_FOLDER']):
                        file_path = alt_path.replace(current_app.config['UPLOAD_FOLDER'] + os.sep, '', 1)
                    else:
                        file_path = alt_path.replace('uploads/', '', 1) if alt_path.startswith('uploads/') else alt_path
                    found = True
                    current_app.logger.info(f'Found PDF at alternative path: {alt_path}, using file_path: {file_path}')
                    break
            
            if not found:
                current_app.logger.error(f'PDF file not found at: {full_path}, stored path: {book.pdf_path}, UPLOAD_FOLDER: {current_app.config["UPLOAD_FOLDER"]}')
                flash('PDF file not found on server.', 'error')
                # Redirect to the correct library based on book type
                library_route = f'{book.library_type}_library' if book.library_type in ['bartender', 'chef'] else 'bartender_library'
                return redirect(url_for(f'knowledge.{library_route}'))
        
        # Use send_from_directory to serve the file directly
        # file_path should be relative to UPLOAD_FOLDER (e.g., 'books/pdfs/filename.pdf')
        try:
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
    """Edit an existing book"""
    from utils.db_helpers import ensure_schema_updates
    ensure_schema_updates()
    
    try:
        org_filter = get_organization_filter(Book)
        book = Book.query.filter(org_filter).filter_by(id=book_id).first_or_404()
        
        title = request.form.get('title', '').strip()
        
        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for(f'knowledge.{book.library_type}_library'))
        
        # Update book details
        book.title = title
        book.author = None  # Author field removed
        
        # Handle PDF upload (optional - only if new file is provided)
        pdf_file = request.files.get('pdf_file')
        pdf_updated = False
        if pdf_file and pdf_file.filename != '':
            if not allowed_file(pdf_file.filename) or not pdf_file.filename.lower().endswith('.pdf'):
                flash('Only PDF files are allowed.', 'error')
                return redirect(url_for(f'knowledge.{book.library_type}_library'))
            
            # Delete old PDF file
            if book.pdf_path:
                old_pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.pdf_path.replace('uploads/', '', 1))
                try:
                    if os.path.exists(old_pdf_path):
                        os.remove(old_pdf_path)
                except Exception as e:
                    current_app.logger.warning(f'Could not delete old PDF: {str(e)}')
            
            # Save new PDF
            pdf_path = save_uploaded_file(pdf_file, 'books/pdfs')
            if pdf_path:
                book.pdf_path = pdf_path
                pdf_updated = True
        
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
        elif pdf_updated:
            # If PDF was updated but no new cover image provided, extract first page from new PDF
            pdf_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.pdf_path.replace('uploads/', '', 1))
            if os.path.exists(pdf_full_path):
                # Delete old cover if it was auto-generated from PDF
                if book.cover_image_path:
                    old_cover_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover_image_path.replace('uploads/', '', 1))
                    try:
                        if os.path.exists(old_cover_path):
                            os.remove(old_cover_path)
                    except Exception as e:
                        current_app.logger.warning(f'Could not delete old cover: {str(e)}')
                
                # Extract first page from new PDF
                cover_image_path = extract_pdf_first_page_as_image(pdf_full_path)
                if cover_image_path:
                    book.cover_image_path = cover_image_path
                else:
                    current_app.logger.warning(f'Failed to extract cover image from updated PDF: {book.pdf_path}')
        
        # Verify files exist before committing
        if book.pdf_path:
            pdf_check_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.pdf_path.replace('uploads/', '', 1))
            if not os.path.exists(pdf_check_path):
                db.session.rollback()
                flash('Error: PDF file was not saved correctly.', 'error')
                return redirect(url_for(f'knowledge.{book.library_type}_library'))
        
        if book.cover_image_path:
            cover_check_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover_image_path.replace('uploads/', '', 1))
            if not os.path.exists(cover_check_path):
                current_app.logger.warning(f'Cover image file not found at: {cover_check_path}, but continuing...')
        
        db.session.commit()
        
        flash('Book updated successfully!', 'success')
        return redirect(url_for(f'knowledge.{book.library_type}_library'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error editing book: {str(e)}', exc_info=True)
        flash(f'Error editing book: {str(e)}', 'error')
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
        
        # Delete book record
        db.session.delete(book)
        db.session.commit()
        
        flash('Book deleted successfully!', 'success')
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

