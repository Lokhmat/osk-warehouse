SELECT
    application_id as id,
    serial_number,
    description,
    type,
    status,
    created_by_id,
    finished_by_id,
    sent_from_warehouse_id,
    sent_to_warehouse_id,
    linked_to_application_id,
    payload,
    created_at,
    updated_at
FROM
    app.applications
WHERE
    application_id = :application_id
;