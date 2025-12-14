# Chef & Bartender - User Guide

## Welcome to Chef & Bartender! 🍹

**Chef & Bartender** is a comprehensive recipe and inventory management system designed specifically for restaurants, bars, and culinary professionals. Whether you're a Chef, Bartender, Manager, or Purchase Manager, this platform helps you manage recipes, track ingredients, calculate costs, and streamline your operations.

---

## What is Chef & Bartender?

Chef & Bartender is a web-based application that helps you:
- **Manage your inventory** - Track all products, ingredients, and suppliers in one place
- **Create and store recipes** - Build recipes for cocktails, mocktails, beverages, and dishes
- **Calculate costs automatically** - Get instant cost calculations for any recipe
- **Manage purchase orders** - Create and track orders from suppliers
- **Access knowledge resources** - Browse recipe books and reference materials
- **Generate reports** - Track purchase history and analyze spending

---

## User Roles & Access

The system has different access levels based on your role:

### 👨‍🍳 **Chef**
- Access to Recipe Center (Recipes & Secondary Ingredients)
- Create and manage purchase orders
- View order history
- Access Kitchen Checklist
- Access Chef Library (Knowledge Hub)

### 🍸 **Bartender**
- Access to Recipe Center (Recipes & Secondary Ingredients)
- Create and manage purchase orders
- View order history
- Access Bar Checklist
- Access Bartender Library (Knowledge Hub)

### 👔 **Manager**
- **Full access** to all features
- Review and approve purchase orders from Chefs/Bartenders
- Access both Bar and Kitchen Checklists
- Access both Chef and Bartender Libraries
- View purchase history reports
- Manage knowledge hub books (add, edit, delete)

### 💼 **Purchase Manager**
- Manage purchase orders (view all orders, update status)
- Access Purchase History reports
- View Master List (read-only)
- Cannot create recipes or purchase orders

### 💰 **Cost Controller**
- View-only access to Master List
- Access Purchase History reports
- Cannot create or modify recipes or orders

---

## Getting Started

### 1. **Registration & Login**
- Click "Register" to create your account
- Fill in your details: username, email, password, name, organization, and role
- Select your country and currency
- After registration, log in with your credentials

### 2. **Master List** (Inventory Management)
The Master List is your central inventory database:
- **View all products** - See all ingredients with codes, descriptions, suppliers, and costs
- **Add products** - Click the "+" button to add new items individually
- **Bulk upload** - Use Excel format to upload multiple products at once
- **Search & filter** - Quickly find products by name, code, or supplier
- **Update costs** - Edit product prices as they change

**Excel Upload Format:**
- Columns: UNIQUE ITEM #, CODE, DESCRIPTION*, SUPPLIER*, CATEGORY*, SUB CATEGORY*, QUANTITY, COST/UNIT (AED)*
- * = Required fields

### 3. **Recipe Center**

#### **Recipes**
Create and manage recipes for:
- **Cocktails** - Alcoholic beverages
- **Mocktails** - Non-alcoholic beverages
- **Beverages** - Other drinks

**How to create a recipe:**
1. Go to Recipe Center → Recipes
2. Click "Add New Recipe"
3. Enter recipe name, category, and description
4. Add ingredients from your Master List
5. Specify quantities for each ingredient
6. Add method/instructions
7. Upload an image (optional)
8. Save - the system automatically calculates the total cost

**Recipe Features:**
- Automatic cost calculation
- Batch summary (shows ingredient breakdown by category)
- Cost percentage calculation
- Recipe codes (REC-####) for easy reference
- Nested recipes (use one recipe as an ingredient in another)

#### **Secondary Ingredients**
Create homemade ingredients (syrups, infusions, house-made items):
1. Go to Recipe Center → Secondary Ingredients
2. Click "Add New Secondary Ingredient"
3. Name your ingredient
4. Link base products from Master List
5. Specify quantities
6. System calculates cost per unit automatically

---

## Purchase Management

### **Purchase Order**
Create new purchase orders:
1. Go to Purchase Center → Purchase Order
2. Add items using the "+" button
3. Type item name in Description - system auto-fills Code, Quantity, Supplier, Sub Category, and Cost per Unit
4. Enter Order Quantity (editable, supports decimals)
5. Click "Create Purchase Request"
6. System generates Order Number and Date/Time
7. Optional: Download PDF of the order

**Note:** Orders from Chefs/Bartenders go to Manager for approval first.

### **Order List**
- View all orders you've created
- See order status (Pending, Order Placed, Order Received, etc.)
- Track order details and history

### **To Order** (Purchase Managers & Managers)
- View all pending orders
- Update order status:
  - **Order Placed** - When order is placed with supplier
  - **Order Received** - When items are received
  - **Order Cancelled** - If order needs to be cancelled
- Enter invoice details when order is received
- Update received quantities
- Generate PDF reports

### **Purchase History** (Managers & Purchase Managers)
- Generate reports on received items
- Filter by date range
- Filter by supplier(s)
- View detailed breakdown: Date, Code, Description, Cost, Quantity, Supplier, Total Cost

---

## Knowledge Hub

Access reference materials and recipe books:

### **Chef Library**
- Browse PDF recipe books
- View book covers
- Click to read full book
- Managers can add, edit, or delete books

### **Bartender Library**
- Browse PDF recipe books
- View book covers
- Click to read full book
- Managers can add, edit, or delete books

**For Managers:**
- Click the "+" button to add new books
- Upload PDF file (cover image auto-generated from first page)
- Drag and drop PDFs onto the "+" button
- Edit or delete existing books

---

## Checklists

### **Bar Checklist** (Managers & Bartenders)
- Access bar-specific checklists
- Track daily bar operations

### **Kitchen Checklist** (Managers & Chefs)
- Access kitchen-specific checklists
- Track daily kitchen operations

---

## Tips & Best Practices

### **Cost Management**
- Update product costs regularly in Master List
- System automatically recalculates recipe costs when prices change
- Use cost percentage to set selling prices and maintain profit margins

### **Recipe Organization**
- Use clear, descriptive recipe names
- Add detailed methods for consistency
- Upload images for visual reference
- Use recipe codes for easy lookup

### **Purchase Orders**
- Review quantities carefully before submitting
- Managers should verify orders before approval
- Update received quantities promptly for accurate inventory tracking
- Use Purchase History to analyze spending patterns

### **Inventory Tracking**
- Keep Master List updated with current products
- Use bulk upload for large inventory additions
- Regularly review and update costs
- Organize by supplier for easier purchasing

---

## Navigation Tips

- **Dropdown menus** - Hover over category names to see sub-options
- **Search bars** - Use search to quickly find recipes, products, or orders
- **Filter ribbons** - Use filters to narrow down results by category, supplier, or date
- **Table headers** - Click to sort, scroll to see more rows (headers stay visible)

---

## Need Help?

- Check the **About** page for more information
- Use the **Contact** page to reach out
- Review your **Profile** to update account information
- Ensure your role has the correct permissions for the features you need

---

## Quick Reference

| Feature | Chef | Bartender | Manager | Purchase Manager | Cost Controller |
|---------|------|-----------|---------|------------------|-----------------|
| Master List | View | View | View | View | View |
| Recipes | Create/Edit | Create/Edit | Create/Edit | - | View |
| Purchase Orders | Create | Create | Create | View | - |
| Approve Orders | - | - | Yes | - | - |
| Purchase History | - | - | Yes | Yes | Yes |
| Knowledge Hub | Yes | Yes | Yes | - | - |
| Checklists | Kitchen | Bar | Both | - | - |

---

**Welcome aboard! Start by exploring the Master List and creating your first recipe. Happy cooking and mixing! 🍹👨‍🍳**

