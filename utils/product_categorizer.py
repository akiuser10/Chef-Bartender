"""
Product categorization utility using AI/keyword matching
"""
import re
from typing import Tuple, Optional


# Category mapping: Main categories
MAIN_CATEGORIES = {
    'Food': 'Food',
    'Alcoholic': 'Beverage',  # Alcoholic beverages go under Beverage category
    'Non Alcoholic': 'Beverage'  # Non-alcoholic beverages go under Beverage category
}

# Sub-category keywords mapping
SUB_CATEGORY_KEYWORDS = {
    # Alcoholic beverages
    'Vodka': ['vodka', 'vodka', 'smirnoff', 'grey goose', 'belvedere', 'absolut', 'ketel one'],
    'Gin': ['gin', 'tanqueray', 'bombay', 'hendricks', 'beefeater', 'gordon', 'sapphire'],
    'Rum': ['rum', 'bacardi', 'captain morgan', 'malibu', 'mount gay', 'appleton', 'havana'],
    'Tequila': ['tequila', 'patron', 'don julio', 'jose cuervo', 'herradura', '1800'],
    'Liqueur': ['liqueur', 'baileys', 'kahlua', 'cointreau', 'grand marnier', 'amaretto', 'frangelico', 'chambord'],
    'Brandy': ['brandy', 'cognac', 'hennessy', 'remy martin', 'courvoisier', 'martell'],
    'Cognac': ['cognac', 'hennessy', 'remy martin', 'courvoisier', 'martell', 'hine'],
    'Armagnac': ['armagnac'],
    'Calvados': ['calvados'],
    'Grappa': ['grappa'],
    'Pisco': ['pisco'],
    'American Whiskey': ['bourbon', 'tennessee', 'jack daniel', 'jim beam', 'maker mark', 'wild turkey', 'woodford'],
    'Irish Whiskey': ['irish whiskey', 'jameson', 'bushmills', 'tullamore', 'redbreast'],
    'Scotch Blended Whisky': ['scotch', 'blended', 'johnnie walker', 'chivas', 'ballantines', 'famous grouse', 'j&b'],
    'Scotch Single Malt': ['single malt', 'glenlivet', 'macallan', 'glenfiddich', 'lagavulin', 'ardbeg', 'laphroaig'],
    'Japanese Whiskey': ['japanese whiskey', 'yamazaki', 'hibiki', 'hakushu', 'nikka'],
    'Indian Whisky': ['indian whisky', 'amrut', 'paul john', 'radico'],
    'Other Whisky': ['whisky', 'whiskey', 'rye', 'canadian'],
    'Amaro': ['amaro', 'aperol', 'campari', 'fernet', 'cynar'],
    'Vermouth': ['vermouth', 'martini', 'noilly prat', 'dolin'],
    'Red Wine': ['red wine', 'cabernet', 'merlot', 'pinot noir', 'shiraz', 'syrah', 'malbec', 'zinfandel', 'sangiovese'],
    'White Wine': ['white wine', 'chardonnay', 'sauvignon blanc', 'pinot grigio', 'riesling', 'moscato', 'gewurztraminer'],
    'Rose Wine': ['rose wine', 'rosé', 'provence'],
    'Sparkling Wine': ['sparkling', 'champagne', 'prosecco', 'cava', 'spumante'],
    
    # Non-alcoholic beverages
    'Syrup': ['syrup', 'simple syrup', 'grenadine', 'agave', 'honey syrup', 'maple syrup'],
    'Puree': ['puree', 'purée', 'mango puree', 'strawberry puree', 'passion fruit puree'],
    'Frozen Puree': ['frozen puree', 'frozen purée'],
    'Frozen Berry': ['frozen berry', 'frozen berries', 'frozen strawberry', 'frozen blueberry'],
    'Fresh Berry': ['fresh berry', 'fresh berries', 'strawberry', 'blueberry', 'raspberry', 'blackberry'],
    'Fresh Juice': ['fresh juice', 'fresh orange juice', 'fresh lemon juice', 'fresh lime juice', 'fresh grapefruit juice'],
    'Packet Juice': ['packet juice', 'boxed juice', 'tetra pack juice', 'canned juice'],
    'Water': ['water', 'mineral water', 'sparkling water', 'still water'],
    'Soft Beverage': ['soft drink', 'soda', 'cola', 'pepsi', 'coca cola', 'fanta', 'sprite', '7up'],
    'Areated Beverage': ['aerated', 'carbonated', 'soda water', 'tonic water', 'ginger ale'],
    
    # Food items
    'Fruit': ['fruit', 'apple', 'banana', 'orange', 'lemon', 'lime', 'grapefruit', 'pineapple', 'mango', 'papaya'],
    'Vegetable': ['vegetable', 'tomato', 'cucumber', 'onion', 'garlic', 'pepper', 'carrot', 'celery', 'lettuce'],
    'Spice': ['spice', 'cinnamon', 'nutmeg', 'clove', 'cardamom', 'star anise', 'vanilla bean', 'peppercorn'],
    'Herb': ['herb', 'basil', 'mint', 'rosemary', 'thyme', 'oregano', 'sage', 'parsley', 'cilantro', 'dill'],
    'Fresh Herbs': ['fresh herb', 'fresh basil', 'fresh mint', 'fresh rosemary', 'fresh thyme'],
    'Fish': ['fish', 'salmon', 'tuna', 'cod', 'sea bass', 'snapper', 'mackerel'],
    'Shell Fish': ['shellfish', 'shrimp', 'prawn', 'lobster', 'crab', 'scallop', 'mussel', 'oyster', 'clam'],
    'Seafood': ['seafood', 'squid', 'octopus', 'cuttlefish'],
    'Meat': ['meat', 'beef', 'chicken', 'pork', 'lamb', 'veal', 'turkey', 'duck'],
    'Egg': ['egg', 'eggs', 'quail egg', 'duck egg'],
    'Dry Fruits': ['dry fruit', 'dried fruit', 'raisin', 'date', 'prune', 'apricot', 'fig'],
    'Dry Nuts': ['dry nut', 'dried nut', 'almond', 'walnut', 'cashew', 'pistachio', 'hazelnut', 'pecan'],
    'Nuts': ['nut', 'almond', 'walnut', 'cashew', 'pistachio', 'hazelnut', 'pecan', 'macadamia'],
    'Milk': ['milk', 'whole milk', 'skim milk', 'full cream milk'],
    'Plant base Milk': ['plant milk', 'almond milk', 'soy milk', 'oat milk', 'coconut milk', 'rice milk', 'cashew milk'],
    'Cheese': ['cheese', 'cheddar', 'mozzarella', 'parmesan', 'feta', 'goat cheese', 'brie', 'camembert'],
    'Yoghurt': ['yoghurt', 'yogurt', 'greek yogurt', 'plain yogurt'],
    'Molecular': ['molecular', 'spherification', 'foam', 'gel', 'agar', 'sodium alginate'],
    'Tea': ['tea', 'black tea', 'green tea', 'oolong', 'jasmine tea', 'earl grey', 'chai'],
    'Coffee': ['coffee', 'espresso', 'arabica', 'robusta', 'coffee bean', 'ground coffee'],
    'Sugar': ['sugar', 'white sugar', 'brown sugar', 'caster sugar', 'icing sugar', 'demerara'],
    'Salt': ['salt', 'sea salt', 'rock salt', 'kosher salt', 'himalayan salt'],
    'Flower': ['flower', 'edible flower', 'lavender', 'rose petal', 'hibiscus', 'elderflower'],
    'Seed': ['seed', 'sesame seed', 'chia seed', 'flax seed', 'pumpkin seed', 'sunflower seed'],
    'Jam': ['jam', 'preserve', 'marmalade', 'fruit jam'],
    'Dry Goods': ['dry good', 'flour', 'rice', 'pasta', 'noodle', 'couscous', 'quinoa', 'barley'],
    'Chocolate': ['chocolate', 'dark chocolate', 'milk chocolate', 'white chocolate', 'cocoa', 'cacao']
}


def categorize_product(description: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Categorize a product based on its description/name using intelligent keyword matching.
    Returns (category, sub_category) tuple.
    
    Category can be: 'Food', 'Beverage' (for both Alcoholic and Non-Alcoholic)
    Sub-category will be one of the specific types listed.
    
    Args:
        description: Product name/description
        
    Returns:
        Tuple of (main_category, sub_category) or (None, None) if no match
    """
    if not description:
        return None, None
    
    description_lower = description.lower().strip()
    
    # Check for alcoholic beverages first (more specific keywords)
    alcoholic_keywords = [
        'vodka', 'gin', 'rum', 'tequila', 'whiskey', 'whisky', 'bourbon', 'scotch',
        'red wine', 'white wine', 'rose wine', 'sparkling wine', 'champagne', 'prosecco', 
        'beer', 'lager', 'ale', 'cider', 'stout', 'ipa',
        'brandy', 'cognac', 'armagnac', 'calvados', 'grappa', 'pisco',
        'liqueur', 'amaro', 'vermouth', 'sake', 'soju', 'mezcal'
    ]
    
    is_alcoholic = any(keyword in description_lower for keyword in alcoholic_keywords)
    
    # Check for non-alcoholic beverages (but exclude if already identified as alcoholic)
    non_alcoholic_keywords = [
        'juice', 'syrup', 'soda', 'cola', 'water', 'tonic', 'ginger ale',
        'soft drink', 'mocktail', 'smoothie', 'milkshake', 'lemonade', 'iced tea'
    ]
    
    is_non_alcoholic_beverage = not is_alcoholic and any(keyword in description_lower for keyword in non_alcoholic_keywords)
    
    # Determine main category
    main_category = None
    if is_alcoholic or is_non_alcoholic_beverage:
        main_category = 'Beverage'  # Both alcoholic and non-alcoholic go under Beverage
    else:
        # Check if it's clearly food
        food_keywords = [
            'meat', 'chicken', 'beef', 'pork', 'lamb', 'fish', 'seafood', 'shellfish',
            'vegetable', 'fruit', 'berry', 'cheese', 'milk', 'yoghurt', 'yogurt',
            'egg', 'flour', 'rice', 'pasta', 'noodle', 'spice', 'herb', 'seed',
            'chocolate', 'sugar', 'salt', 'tea', 'coffee', 'jam', 'puree',
            'nut', 'almond', 'walnut', 'cashew', 'dry fruit', 'dry nut'
        ]
        if any(keyword in description_lower for keyword in food_keywords):
            main_category = 'Food'
    
    # Find sub-category by matching keywords (prioritize longer/more specific matches)
    sub_category = None
    best_match_score = 0
    best_match_subcat = None
    
    for sub_cat, keywords in SUB_CATEGORY_KEYWORDS.items():
        score = 0
        matched_keywords = []
        for keyword in keywords:
            if keyword in description_lower:
                # Longer keywords get higher priority
                keyword_score = len(keyword) * 2  # Weight longer matches more
                # Exact word matches get bonus
                if re.search(r'\b' + re.escape(keyword) + r'\b', description_lower):
                    keyword_score *= 1.5
                score += keyword_score
                matched_keywords.append(keyword)
        
        if score > best_match_score:
            best_match_score = score
            best_match_subcat = sub_cat
    
    sub_category = best_match_subcat
    
    # If no sub-category found but we have a main category, use a default
    if main_category and not sub_category:
        if main_category == 'Beverage':
            if is_alcoholic:
                sub_category = 'Other'
            else:
                sub_category = 'Other'
        else:
            sub_category = 'Other'
    
    return main_category, sub_category


def categorize_with_ai(description: str, use_ai_api: bool = False, api_key: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Categorize product using AI API (if enabled) or fallback to keyword matching.
    
    Args:
        description: Product name/description
        use_ai_api: Whether to use AI API (requires API key)
        api_key: API key for AI service (e.g., OpenAI)
        
    Returns:
        Tuple of (main_category, sub_category)
    """
    if use_ai_api and api_key:
        # TODO: Implement AI API integration (OpenAI, etc.)
        # For now, fallback to keyword matching
        pass
    
    # Use keyword-based categorization
    return categorize_product(description)

