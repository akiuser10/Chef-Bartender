"""
Currency utility functions and data
"""
# Comprehensive list of world currencies
CURRENCIES = {
    'AED': {'name': 'UAE Dirham', 'symbol': 'AED', 'position': 'prefix'},
    'USD': {'name': 'US Dollar', 'symbol': '$', 'position': 'prefix'},
    'EUR': {'name': 'Euro', 'symbol': '€', 'position': 'prefix'},
    'GBP': {'name': 'British Pound', 'symbol': '£', 'position': 'prefix'},
    'JPY': {'name': 'Japanese Yen', 'symbol': '¥', 'position': 'prefix'},
    'AUD': {'name': 'Australian Dollar', 'symbol': 'A$', 'position': 'prefix'},
    'CAD': {'name': 'Canadian Dollar', 'symbol': 'C$', 'position': 'prefix'},
    'CHF': {'name': 'Swiss Franc', 'symbol': 'CHF', 'position': 'prefix'},
    'CNY': {'name': 'Chinese Yuan', 'symbol': '¥', 'position': 'prefix'},
    'INR': {'name': 'Indian Rupee', 'symbol': '₹', 'position': 'prefix'},
    'SGD': {'name': 'Singapore Dollar', 'symbol': 'S$', 'position': 'prefix'},
    'HKD': {'name': 'Hong Kong Dollar', 'symbol': 'HK$', 'position': 'prefix'},
    'SAR': {'name': 'Saudi Riyal', 'symbol': 'SAR', 'position': 'prefix'},
    'QAR': {'name': 'Qatari Riyal', 'symbol': 'QAR', 'position': 'prefix'},
    'KWD': {'name': 'Kuwaiti Dinar', 'symbol': 'KWD', 'position': 'prefix'},
    'BHD': {'name': 'Bahraini Dinar', 'symbol': 'BHD', 'position': 'prefix'},
    'OMR': {'name': 'Omani Rial', 'symbol': 'OMR', 'position': 'prefix'},
    'JOD': {'name': 'Jordanian Dinar', 'symbol': 'JOD', 'position': 'prefix'},
    'EGP': {'name': 'Egyptian Pound', 'symbol': 'EGP', 'position': 'prefix'},
    'ZAR': {'name': 'South African Rand', 'symbol': 'R', 'position': 'prefix'},
    'NZD': {'name': 'New Zealand Dollar', 'symbol': 'NZ$', 'position': 'prefix'},
    'SEK': {'name': 'Swedish Krona', 'symbol': 'kr', 'position': 'suffix'},
    'NOK': {'name': 'Norwegian Krone', 'symbol': 'kr', 'position': 'suffix'},
    'DKK': {'name': 'Danish Krone', 'symbol': 'kr', 'position': 'suffix'},
    'PLN': {'name': 'Polish Zloty', 'symbol': 'zł', 'position': 'suffix'},
    'RUB': {'name': 'Russian Ruble', 'symbol': '₽', 'position': 'suffix'},
    'TRY': {'name': 'Turkish Lira', 'symbol': '₺', 'position': 'prefix'},
    'MXN': {'name': 'Mexican Peso', 'symbol': '$', 'position': 'prefix'},
    'BRL': {'name': 'Brazilian Real', 'symbol': 'R$', 'position': 'prefix'},
    'ARS': {'name': 'Argentine Peso', 'symbol': '$', 'position': 'prefix'},
    'CLP': {'name': 'Chilean Peso', 'symbol': '$', 'position': 'prefix'},
    'COP': {'name': 'Colombian Peso', 'symbol': '$', 'position': 'prefix'},
    'THB': {'name': 'Thai Baht', 'symbol': '฿', 'position': 'prefix'},
    'MYR': {'name': 'Malaysian Ringgit', 'symbol': 'RM', 'position': 'prefix'},
    'IDR': {'name': 'Indonesian Rupiah', 'symbol': 'Rp', 'position': 'prefix'},
    'PHP': {'name': 'Philippine Peso', 'symbol': '₱', 'position': 'prefix'},
    'VND': {'name': 'Vietnamese Dong', 'symbol': '₫', 'position': 'prefix'},
    'KRW': {'name': 'South Korean Won', 'symbol': '₩', 'position': 'prefix'},
    'TWD': {'name': 'Taiwan Dollar', 'symbol': 'NT$', 'position': 'prefix'},
    'PKR': {'name': 'Pakistani Rupee', 'symbol': '₨', 'position': 'prefix'},
    'BDT': {'name': 'Bangladeshi Taka', 'symbol': '৳', 'position': 'prefix'},
    'LKR': {'name': 'Sri Lankan Rupee', 'symbol': 'Rs', 'position': 'prefix'},
    'NPR': {'name': 'Nepalese Rupee', 'symbol': '₨', 'position': 'prefix'},
    'ILS': {'name': 'Israeli Shekel', 'symbol': '₪', 'position': 'prefix'},
    'LBP': {'name': 'Lebanese Pound', 'symbol': 'L£', 'position': 'prefix'},
    'IQD': {'name': 'Iraqi Dinar', 'symbol': 'IQD', 'position': 'prefix'},
    'IRR': {'name': 'Iranian Rial', 'symbol': 'IRR', 'position': 'prefix'},
    'AFN': {'name': 'Afghan Afghani', 'symbol': '؋', 'position': 'prefix'},
    'NGN': {'name': 'Nigerian Naira', 'symbol': '₦', 'position': 'prefix'},
    'KES': {'name': 'Kenyan Shilling', 'symbol': 'KSh', 'position': 'prefix'},
    'UGX': {'name': 'Ugandan Shilling', 'symbol': 'USh', 'position': 'prefix'},
    'TZS': {'name': 'Tanzanian Shilling', 'symbol': 'TSh', 'position': 'prefix'},
    'ETB': {'name': 'Ethiopian Birr', 'symbol': 'ETB', 'position': 'prefix'},
    'GHS': {'name': 'Ghanaian Cedi', 'symbol': 'GH₵', 'position': 'prefix'},
    'XOF': {'name': 'West African CFA Franc', 'symbol': 'CFA', 'position': 'prefix'},
    'XAF': {'name': 'Central African CFA Franc', 'symbol': 'FCFA', 'position': 'prefix'},
    'MAD': {'name': 'Moroccan Dirham', 'symbol': 'MAD', 'position': 'prefix'},
    'TND': {'name': 'Tunisian Dinar', 'symbol': 'TND', 'position': 'prefix'},
    'DZD': {'name': 'Algerian Dinar', 'symbol': 'DZD', 'position': 'prefix'},
    'LYD': {'name': 'Libyan Dinar', 'symbol': 'LYD', 'position': 'prefix'},
    'CZK': {'name': 'Czech Koruna', 'symbol': 'Kč', 'position': 'suffix'},
    'HUF': {'name': 'Hungarian Forint', 'symbol': 'Ft', 'position': 'suffix'},
    'RON': {'name': 'Romanian Leu', 'symbol': 'lei', 'position': 'suffix'},
    'BGN': {'name': 'Bulgarian Lev', 'symbol': 'лв', 'position': 'suffix'},
    'HRK': {'name': 'Croatian Kuna', 'symbol': 'kn', 'position': 'suffix'},
    'RSD': {'name': 'Serbian Dinar', 'symbol': 'дин', 'position': 'suffix'},
    'UAH': {'name': 'Ukrainian Hryvnia', 'symbol': '₴', 'position': 'prefix'},
    'BYN': {'name': 'Belarusian Ruble', 'symbol': 'Br', 'position': 'suffix'},
    'KZT': {'name': 'Kazakhstani Tenge', 'symbol': '₸', 'position': 'prefix'},
    'UZS': {'name': 'Uzbekistani Som', 'symbol': 'UZS', 'position': 'prefix'},
    'AMD': {'name': 'Armenian Dram', 'symbol': '֏', 'position': 'prefix'},
    'GEL': {'name': 'Georgian Lari', 'symbol': '₾', 'position': 'prefix'},
    'AZN': {'name': 'Azerbaijani Manat', 'symbol': '₼', 'position': 'prefix'},
    'ISK': {'name': 'Icelandic Krona', 'symbol': 'kr', 'position': 'suffix'},
    'FJD': {'name': 'Fijian Dollar', 'symbol': 'FJ$', 'position': 'prefix'},
    'PGK': {'name': 'Papua New Guinean Kina', 'symbol': 'K', 'position': 'prefix'},
    'XPF': {'name': 'CFP Franc', 'symbol': '₣', 'position': 'prefix'},
}

# Countries with their currencies
COUNTRIES = {
    'AE': {'name': 'United Arab Emirates', 'currency': 'AED'},
    'US': {'name': 'United States', 'currency': 'USD'},
    'GB': {'name': 'United Kingdom', 'currency': 'GBP'},
    'CA': {'name': 'Canada', 'currency': 'CAD'},
    'AU': {'name': 'Australia', 'currency': 'AUD'},
    'NZ': {'name': 'New Zealand', 'currency': 'NZD'},
    'JP': {'name': 'Japan', 'currency': 'JPY'},
    'CN': {'name': 'China', 'currency': 'CNY'},
    'IN': {'name': 'India', 'currency': 'INR'},
    'SG': {'name': 'Singapore', 'currency': 'SGD'},
    'HK': {'name': 'Hong Kong', 'currency': 'HKD'},
    'SA': {'name': 'Saudi Arabia', 'currency': 'SAR'},
    'QA': {'name': 'Qatar', 'currency': 'QAR'},
    'KW': {'name': 'Kuwait', 'currency': 'KWD'},
    'BH': {'name': 'Bahrain', 'currency': 'BHD'},
    'OM': {'name': 'Oman', 'currency': 'OMR'},
    'JO': {'name': 'Jordan', 'currency': 'JOD'},
    'EG': {'name': 'Egypt', 'currency': 'EGP'},
    'ZA': {'name': 'South Africa', 'currency': 'ZAR'},
    'DE': {'name': 'Germany', 'currency': 'EUR'},
    'FR': {'name': 'France', 'currency': 'EUR'},
    'IT': {'name': 'Italy', 'currency': 'EUR'},
    'ES': {'name': 'Spain', 'currency': 'EUR'},
    'NL': {'name': 'Netherlands', 'currency': 'EUR'},
    'BE': {'name': 'Belgium', 'currency': 'EUR'},
    'AT': {'name': 'Austria', 'currency': 'EUR'},
    'CH': {'name': 'Switzerland', 'currency': 'CHF'},
    'SE': {'name': 'Sweden', 'currency': 'SEK'},
    'NO': {'name': 'Norway', 'currency': 'NOK'},
    'DK': {'name': 'Denmark', 'currency': 'DKK'},
    'PL': {'name': 'Poland', 'currency': 'PLN'},
    'RU': {'name': 'Russia', 'currency': 'RUB'},
    'TR': {'name': 'Turkey', 'currency': 'TRY'},
    'MX': {'name': 'Mexico', 'currency': 'MXN'},
    'BR': {'name': 'Brazil', 'currency': 'BRL'},
    'AR': {'name': 'Argentina', 'currency': 'ARS'},
    'CL': {'name': 'Chile', 'currency': 'CLP'},
    'CO': {'name': 'Colombia', 'currency': 'COP'},
    'TH': {'name': 'Thailand', 'currency': 'THB'},
    'MY': {'name': 'Malaysia', 'currency': 'MYR'},
    'ID': {'name': 'Indonesia', 'currency': 'IDR'},
    'PH': {'name': 'Philippines', 'currency': 'PHP'},
    'VN': {'name': 'Vietnam', 'currency': 'VND'},
    'KR': {'name': 'South Korea', 'currency': 'KRW'},
    'TW': {'name': 'Taiwan', 'currency': 'TWD'},
    'PK': {'name': 'Pakistan', 'currency': 'PKR'},
    'BD': {'name': 'Bangladesh', 'currency': 'BDT'},
    'LK': {'name': 'Sri Lanka', 'currency': 'LKR'},
    'NP': {'name': 'Nepal', 'currency': 'NPR'},
    'IL': {'name': 'Israel', 'currency': 'ILS'},
    'LB': {'name': 'Lebanon', 'currency': 'LBP'},
    'IQ': {'name': 'Iraq', 'currency': 'IQD'},
    'IR': {'name': 'Iran', 'currency': 'IRR'},
    'AF': {'name': 'Afghanistan', 'currency': 'AFN'},
    'NG': {'name': 'Nigeria', 'currency': 'NGN'},
    'KE': {'name': 'Kenya', 'currency': 'KES'},
    'UG': {'name': 'Uganda', 'currency': 'UGX'},
    'TZ': {'name': 'Tanzania', 'currency': 'TZS'},
    'ET': {'name': 'Ethiopia', 'currency': 'ETB'},
    'GH': {'name': 'Ghana', 'currency': 'GHS'},
    'MA': {'name': 'Morocco', 'currency': 'MAD'},
    'TN': {'name': 'Tunisia', 'currency': 'TND'},
    'DZ': {'name': 'Algeria', 'currency': 'DZD'},
    'LY': {'name': 'Libya', 'currency': 'LYD'},
    'CZ': {'name': 'Czech Republic', 'currency': 'CZK'},
    'HU': {'name': 'Hungary', 'currency': 'HUF'},
    'RO': {'name': 'Romania', 'currency': 'RON'},
    'BG': {'name': 'Bulgaria', 'currency': 'BGN'},
    'HR': {'name': 'Croatia', 'currency': 'HRK'},
    'RS': {'name': 'Serbia', 'currency': 'RSD'},
    'UA': {'name': 'Ukraine', 'currency': 'UAH'},
    'BY': {'name': 'Belarus', 'currency': 'BYN'},
    'KZ': {'name': 'Kazakhstan', 'currency': 'KZT'},
    'UZ': {'name': 'Uzbekistan', 'currency': 'UZS'},
    'AM': {'name': 'Armenia', 'currency': 'AMD'},
    'GE': {'name': 'Georgia', 'currency': 'GEL'},
    'AZ': {'name': 'Azerbaijan', 'currency': 'AZN'},
    'IS': {'name': 'Iceland', 'currency': 'ISK'},
    'FJ': {'name': 'Fiji', 'currency': 'FJD'},
    'PG': {'name': 'Papua New Guinea', 'currency': 'PGK'},
    'XX': {'name': 'Other', 'currency': 'USD'},  # Default for other countries
}


def get_currency_info(currency_code):
    """Get currency information by code"""
    return CURRENCIES.get(currency_code, CURRENCIES['AED'])


def format_currency(amount, currency_code='AED', decimals=2):
    """
    Format amount with currency symbol
    
    Args:
        amount: The numeric amount to format
        currency_code: ISO currency code (default: AED)
        decimals: Number of decimal places (default: 2)
    
    Returns:
        Formatted string with currency symbol
    """
    currency_info = get_currency_info(currency_code)
    symbol = currency_info['symbol']
    position = currency_info['position']
    
    # Format the amount
    formatted_amount = f"{amount:,.{decimals}f}"
    
    # Add currency symbol based on position
    if position == 'prefix':
        return f"{symbol} {formatted_amount}"
    else:
        return f"{formatted_amount} {symbol}"


def get_country_currency(country_code):
    """Get default currency for a country"""
    country = COUNTRIES.get(country_code)
    if country:
        return country['currency']
    return 'AED'  # Default to AED
