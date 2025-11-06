# ADR 0008: Circle Admin Image Upload Pipeline

- Status: Accepted
- Date: 2025-11-06
- Related Artifacts: `mysite/keeps/views/uploads.py`, `mysite/keeps/tasks.py`, `web/src/features/keeps/`

## Context
- Circle memories (`Keep` records) currently allow any member to attach photos, but product wants tighter control so only circle admins can add shared media.
- The backend already supports asynchronous processing (`MediaUpload`, `KeepMedia`, Celery tasks) yet the authorization model and frontend UX do not enforce admin-only uploads.
- Families expect a modern uploader with drag-and-drop, browse fallback, progress, and clear status once background jobs finish generating thumbnail, gallery, and full-size assets.
- Notifications should alert admins when processing completes or fails so they know whether the keep is ready to publish without refreshing.

## Decision
1. **Restrict upload endpoints to circle admins**  
   - Update `MediaUploadView`/`MediaUploadStatusView` to use an `IsCircleAdmin` permission that verifies the caller’s `CircleMembership.role` is `CIRCLE_ADMIN`.  
   - The serializer outputs remain unchanged so existing consumers continue to function.

2. **Frontend uploader built around `react-dropzone` + TanStack stack**  
   - Introduce `react-dropzone` for drag-and-drop plus file browsing; leverage the HTML file input fallback for accessibility.  
   - Wrap the uploader in a `CircleMediaUploader` component that uses `@tanstack/react-form` for validation (file size, type, caption) and a `useMutation` from `@tanstack/react-query` to post `FormData` to `/api/keeps/uploads/`.
   - Maintain optimistic UI by immediately listing pending files with progress derived from `MediaUploadStatus.progress_percentage`.

3. **Asynchronous processing with deterministic image derivatives**  
   - Preserve the existing Celery pipeline: `validate_media_file` → `process_media_upload` → `generate_image_sizes`. These tasks continue to persist originals and produce 150×150 thumbnails and 800×600 gallery assets before marking uploads `completed`.  
   - Store assets through the configured `get_storage_backend()` so MinIO/S3 behaviour stays consistent; metadata (width/height) is recorded on `KeepMedia`.

4. **Job status tracking and completion notifications**  
   - Expose upload tokens returned from the POST request to the client and poll `/api/keeps/uploads/{id}/status/` (backed by `MediaUploadStatusView`) using React Query with exponential backoff until the job reaches `completed` or `failed`.  
   - Surface status transitions via `sonner` toasts: success when derivatives are ready, error when validation or processing fails, with internationalized messages (`notifications.media.upload_initiated`, `notifications.media.upload_failed`).  
   - Send structured audit logs (`keeps.media.process_success`/`failure`) to the existing logging stack and trigger websocket/webhook hooks when those events are available, keeping room for a richer real-time channel later.

5. **Job status UI within circle keeps**  
   - Add an `UploadManager` panel that lists in-flight uploads with their filename, current status label (Pending, Validating, Processing, Completed, Failed), and progress bar fed by the `progress_percentage` serializer field.  
   - When an upload completes, swap the list item for the rendered media card by refetching the keep detail query; on failure, provide retry/delete affordances gated to admins.

## Rationale
- Tightening upload permissions prevents non-admin members from altering the shared circle gallery, aligning with moderation expectations and privacy commitments.
- `react-dropzone` is lightweight, widely adopted, and fits the Vite/React 19 setup without conflicting dependencies; coupling it with TanStack Query/Form reuses the project’s existing patterns for network state and validation.
- Polling the status endpoint builds on the current API surface with minimal additional backend work while keeping the door open for future push notifications.
- Reusing the existing Celery tasks avoids duplicating image processing logic and guarantees thumbnails/gallery/full-size derivatives are always produced before `KeepMedia` becomes visible.

## Consequences
- Add unit and integration coverage to ensure non-admin members receive `403` responses on upload and status endpoints, and verify admin success paths.  
- Frontend work requires adding `react-dropzone` to `web/package.json` and writing Vitest coverage for the uploader component and polling logic.  
- Operations must monitor Celery queues because admin-only uploads could concentrate traffic through fewer users, making failure notifications more critical.  
- Documentation and onboarding materials need updates to clarify that only circle admins can contribute photos; member UX should guide them to request access when necessary.

## Alternatives Considered
- **Keep member uploads with post-review**: Rejected because moderation queues add latency and complexity while still exposing raw assets before approval.  
- **Direct browser-to-S3 multipart uploads**: Deferred; it complicates permissions and bypasses the existing `MediaUpload` validation/derivative pipeline. The chosen approach keeps server-side validation centralized.  
- **Custom drag-and-drop implementation**: Rejected in favor of `react-dropzone`, which already handles focus, keyboard support, and multiple file selection gracefully.
