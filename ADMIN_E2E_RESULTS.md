# Admin panel verification

- PASS: Admin accounts cannot be moderated/deleted, and multiple dealer service locations produce one account with all cities
- PASS: Admin shows the complete product count, pages without duplicate rows, and finds products beyond the first 250
- PASS: Add Product saves category/item, brand, model, prices and specification values containing colons
- PASS: Archived products remain editable by admin and hidden from buyers; deleting a used category/item is blocked
- PASS: Invalid prices roll back and non-admin accounts cannot create, edit or list admin products
- PASS: Admin buyer details show saved locations before any request exists and accurate purchase counts
- PASS: All moderation states display correctly, held/suspended/banned access is blocked, approval restores verification, and timeline records changes
- PASS: Winning purchases count correctly; products with bid history lock identity but allow price/spec/status edits
- PASS: Product deletion retains winning history and account deletion requires confirmation
- PASS: No admin browser JavaScript errors

Used the real database and temporary products/categories/accounts. Fixture records are removed after testing.
