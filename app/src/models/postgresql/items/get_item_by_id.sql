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
    id=:item_id;
