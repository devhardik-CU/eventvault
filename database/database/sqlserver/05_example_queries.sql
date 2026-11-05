-- Hand-written reference queries (T-SQL). These mirror what the application runs through SQLAlchemy.
-- NOT executed in the development sandbox (no SQL Server available) - run them in Azure Data Studio / SSMS to explore.

-- 1) JOIN: event list with category, organizer and live registration count (3 tables + aggregate)
SELECT e.id, e.title, c.name AS category, u.full_name AS organizer,
       COUNT(CASE WHEN r.status = 'registered' THEN 1 END) AS registered_count, e.capacity
FROM events e
JOIN categories c ON c.id = e.category_id
JOIN users u      ON u.id = e.organizer_id
LEFT JOIN registrations r ON r.event_id = e.id
WHERE e.status = 'published' AND e.end_time >= SYSUTCDATETIME()
GROUP BY e.id, e.title, c.name, u.full_name, e.capacity, e.start_time
ORDER BY e.start_time;

-- 2) JOIN: a participant's registrations with event details
SELECT r.id, r.status, e.title, e.start_time, e.location
FROM registrations r JOIN events e ON e.id = r.event_id
WHERE r.user_id = 1 ORDER BY e.start_time;

-- 3) JOIN: attendee list for an organizer's event
SELECT u.full_name, u.email, r.registered_at
FROM registrations r JOIN users u ON u.id = r.user_id
WHERE r.event_id = 1 AND r.status = 'registered' ORDER BY r.registered_at;

-- 4) The view used by the analytics page
SELECT * FROM vw_event_stats WHERE organizer_id = 1 ORDER BY start_time DESC;

-- 5) TRANSACTION: what the API does when a participant registers (lock event row, validate, insert, audit)
BEGIN TRY
  BEGIN TRANSACTION;
    DECLARE @event_id INT = 1, @user_id INT = 2;
    DECLARE @capacity INT;
    SELECT @capacity = capacity FROM events WITH (UPDLOCK, ROWLOCK) WHERE id = @event_id AND status = 'published';
    IF @capacity IS NULL THROW 50002, 'Event not found or cancelled.', 1;
    IF (SELECT COUNT(*) FROM registrations WHERE event_id = @event_id AND status = 'registered') >= @capacity
      THROW 50003, 'Event is full.', 1;
    INSERT INTO registrations (user_id, event_id, status) VALUES (@user_id, @event_id, 'registered');
    INSERT INTO activity_logs (user_id, action, entity, entity_id) VALUES (@user_id, 'registration_created', 'registration', SCOPE_IDENTITY());
  COMMIT TRANSACTION;
END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
  THROW;
END CATCH;
