INSERT INTO
    app.applications(
        application_id,
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
    )
VALUES
    (
        :application_id,
        :description,
        :type,
        :status,
        :created_by_id,
        :finished_by_id,
        :sent_from_warehouse_id,
        :sent_to_warehouse_id,
        :linked_to_application_id,
        :payload,
        :created_at,
        :updated_at
    ) ON CONFLICT (application_id) DO
UPDATE
SET
    application_id = :application_id
RETURNING
    application_id as id,
    applications.serial_number,
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
;
