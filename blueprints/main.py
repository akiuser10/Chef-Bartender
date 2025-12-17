"""
Main blueprint - handles index, errors, and file uploads
"""
# pyright: reportMissingImports=false
from flask import Blueprint, render_template, send_from_directory, current_app, request, redirect, url_for, flash
from flask_login import login_required, current_user
from utils.permissions import role_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Homepage with recent recipes and hero slides"""
    from datetime import datetime, timedelta
    from models import Recipe, HeroSlide, Book, PurchaseRequest, Product
    from utils.helpers import get_organization_filter
    from sqlalchemy.orm import joinedload
    
    # Fetch 8 most recently created recipes
    org_filter = get_organization_filter(Recipe)
    recent_recipes = Recipe.query.filter(org_filter).options(
        joinedload(Recipe.ingredients)
    ).order_by(Recipe.created_at.desc()).limit(8).all()
    
    # Fetch hero slides from database, filtered by organization and ordered by slide_number
    hero_org_filter = get_organization_filter(HeroSlide)
    hero_slides = HeroSlide.query.filter(hero_org_filter, HeroSlide.is_active == True).order_by(HeroSlide.slide_number).all()
    
    # Fetch books (for Knowledge Hub section) filtered by user role, newest first
    book_org_filter = get_organization_filter(Book)
    recent_books_query = Book.query.filter(book_org_filter)
    
    # Filter books based on user role
    if current_user.is_authenticated:
        user_role = current_user.user_role or ''
        if user_role == 'Bartender':
            # Bartenders can only see bartender library books
            recent_books_query = recent_books_query.filter_by(library_type='bartender')
        elif user_role == 'Chef':
            # Chefs can only see chef library books
            recent_books_query = recent_books_query.filter_by(library_type='chef')
        elif user_role == 'Manager':
            # Managers can see all books
            pass
        else:
            # Other roles see no books
            recent_books_query = recent_books_query.filter_by(id=None)  # Empty result
    else:
        # Non-authenticated users see no books
        recent_books_query = recent_books_query.filter_by(id=None)  # Empty result
    
    recent_books = recent_books_query.order_by(Book.created_at.desc()).all()

    # Build tasks for top hero cards based on user role and data
    tasks = []
    if current_user.is_authenticated:
        role = current_user.user_role or ''

        # Shared org filters
        purchase_org_filter = get_organization_filter(PurchaseRequest)
        product_org_filter = get_organization_filter(Product)

        # Recipe cost review tasks (for Chef, Bartender, Manager)
        if role in ['Chef', 'Bartender', 'Manager']:
            recipe_org_filter = get_organization_filter(Recipe)
            recipe_q = Recipe.query.filter(recipe_org_filter).options(joinedload(Recipe.ingredients))
            pending_cost = sum(1 for r in recipe_q if r.has_missing_cost())
            if pending_cost:
                tasks.append({
                    'key': 'recipe_review',
                    'title': 'Recipes to Review',
                    'count': pending_cost,
                    'subtitle': 'Recipes need cost or data updates',
                    'url': url_for('recipes.recipes_list'),
                    'color_class': 'red-juice'
                })

        # Manager-specific purchase approvals
        if role == 'Manager':
            manager_pending = PurchaseRequest.query.filter(
                purchase_org_filter,
                PurchaseRequest.status == 'Pending Manager Approval'
            ).count()
            if manager_pending:
                tasks.append({
                    'key': 'manager_approvals',
                    'title': 'Orders to Approve',
                    'count': manager_pending,
                    'subtitle': 'Purchase requests awaiting your approval',
                    'url': url_for('purchase.order_list'),
                    'color_class': 'orange-juice'
                })

        # Purchase Manager tasks
        if role == 'Purchase Manager':
            to_order = PurchaseRequest.query.filter(
                purchase_org_filter,
                PurchaseRequest.status == 'Pending'
            ).count()
            if to_order:
                tasks.append({
                    'key': 'to_order',
                    'title': 'Orders to Place',
                    'count': to_order,
                    'subtitle': 'Approved orders waiting to be placed',
                    'url': url_for('purchase.to_order'),
                    'color_class': 'orange-juice'
                })

            # Orders placed but not fully received
            awaiting = [
                pr for pr in PurchaseRequest.query.filter(purchase_org_filter).all()
                if pr.get_overall_status() in ['Order Placed', 'Partially Ordered']
            ]
            if awaiting:
                tasks.append({
                    'key': 'awaiting_delivery',
                    'title': 'Awaiting Delivery',
                    'count': len(awaiting),
                    'subtitle': 'Orders in progress with suppliers',
                    'url': url_for('purchase.purchase_history'),
                    'color_class': 'beige-juice'
                })

    return render_template(
        'index.html',
        recent_recipes=recent_recipes,
        hero_slides=hero_slides,
        recent_books=recent_books,
        tasks=tasks
    )


@main_bp.route('/about')
def about():
    return render_template('about.html')


@main_bp.route('/contact')
def contact():
    return render_template('contact.html')


@main_bp.route('/user-guide')
def user_guide():
    """Display the user guide from USER_GUIDE.md"""
    import os
    import markdown  # type: ignore[import]
    from markupsafe import Markup
    
    try:
        # Get the path to USER_GUIDE.md
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        guide_path = os.path.join(base_dir, 'USER_GUIDE.md')
        
        # Read the markdown file
        with open(guide_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Convert markdown to HTML
        html_content = markdown.markdown(markdown_content, extensions=['extra', 'codehilite'])
        
        return render_template('user_guide.html', guide_content=Markup(html_content))
    except Exception as e:
        current_app.logger.error(f'Error loading user guide: {str(e)}', exc_info=True)
        return render_template('error.html', error='Unable to load user guide'), 500


@main_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    import os
    from flask import abort
    
    # Remove 'uploads/' prefix if present (for consistency)
    if filename.startswith('uploads/'):
        filename = filename.replace('uploads/', '', 1)
    
    # Construct full path
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        current_app.logger.warning(f'File not found: {file_path}, requested filename: {filename}')
        abort(404)
    
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@main_bp.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='Page not found'), 404


@main_bp.errorhandler(500)
def internal_error(error):
    from extensions import db
    db.session.rollback()
    current_app.logger.error(f'Internal Server Error: {str(error)}', exc_info=True)
    return render_template('error.html', error=str(error)), 500


@main_bp.route('/manage-hero-slides')
@login_required
@role_required('Manager')
def manage_hero_slides():
    """Manage hero slides - Manager only"""
    from models import HeroSlide
    from utils.db_helpers import ensure_schema_updates
    from utils.helpers import get_organization_filter
    ensure_schema_updates()
    
    # Fetch hero slides filtered by organization, ordered by slide_number
    org_filter = get_organization_filter(HeroSlide)
    hero_slides = HeroSlide.query.filter(org_filter).order_by(HeroSlide.slide_number).all()
    
    # Ensure we have 5 slides (create empty ones if needed)
    while len(hero_slides) < 5:
        new_slide = HeroSlide(
            slide_number=len(hero_slides),
            title=f'Slide {len(hero_slides) + 1}',
            subtitle='',
            image_path='',
            is_active=False,
            created_by=current_user.id,
            organisation=current_user.organisation if current_user.organisation else ''
        )
        from extensions import db
        db.session.add(new_slide)
        db.session.commit()
        hero_slides.append(new_slide)
    
    return render_template('manage_hero_slides.html', hero_slides=hero_slides)


@main_bp.route('/edit-hero-slide/<int:slide_id>', methods=['GET', 'POST'])
@login_required
@role_required('Manager')
def edit_hero_slide(slide_id):
    """Edit a hero slide - Manager only, organization filtered"""
    from models import HeroSlide
    from extensions import db
    from utils.file_upload import save_hero_slide_image
    from utils.db_helpers import ensure_schema_updates
    from utils.helpers import get_organization_filter
    from flask import abort
    import os
    from datetime import datetime
    
    ensure_schema_updates()
    
    # Fetch slide with organization filter to ensure manager can only edit their organization's slides
    org_filter = get_organization_filter(HeroSlide)
    slide = HeroSlide.query.filter(org_filter, HeroSlide.id == slide_id).first_or_404()
    
    if request.method == 'POST':
        slide.title = request.form.get('title', '').strip()
        slide.subtitle = request.form.get('subtitle', '').strip()
        slide.is_active = request.form.get('is_active') == 'on'
        slide.updated_at = datetime.utcnow()
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Delete old image if exists
                if slide.image_path:
                    # Check if old path is in static/images/hero or uploads/hero-slides
                    if slide.image_path.startswith('images/hero/'):
                        # Old path is in static/images/hero
                        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        old_path = os.path.join(base_dir, 'static', slide.image_path)
                    elif slide.image_path.startswith('uploads/hero-slides/'):
                        # Old path is in uploads (legacy)
                        old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], slide.image_path.replace('uploads/', '', 1))
                    else:
                        # Try both locations
                        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        old_path_static = os.path.join(base_dir, 'static', slide.image_path)
                        old_path_uploads = os.path.join(current_app.config['UPLOAD_FOLDER'], slide.image_path.replace('uploads/', '', 1))
                        old_path = old_path_static if os.path.exists(old_path_static) else old_path_uploads
                    
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except Exception as e:
                            current_app.logger.warning(f'Could not delete old image: {str(e)}')
                
                # Save new image to static/images/hero/
                image_path = save_hero_slide_image(file)
                if image_path:
                    slide.image_path = image_path
        
        db.session.commit()
        flash('Hero slide updated successfully!', 'success')
        return redirect(url_for('main.manage_hero_slides'))
    
    return render_template('edit_hero_slide.html', slide=slide)

