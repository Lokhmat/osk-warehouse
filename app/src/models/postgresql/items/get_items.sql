SELECT 
    id,
    item_name,
    item_type,
    manufacturer,
    model,
    description,
    codes
FROM
    app.items
WHERE 
    NOT is_deleted
    AND (:item_name IS NULL OR item_name LIKE ('%' || :item_name || '%'))
    AND (:item_cat IS NULL OR item_type LIKE ('%' || :item_cat || '%'));
