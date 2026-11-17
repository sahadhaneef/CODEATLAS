# Foundation trust boundaries

Local development only. Bind API/database to loopback. Development bearer tokens are secrets;
never commit .env, expose this mode to a network, or use local Compose database credentials in
production. Runtime role is NOSUPERUSER/NOBYPASSRLS; migrations use a separate owner.

The client cannot establish tenant authority through organization or repository identifiers.
Server tokens choose tenant and principal; repository owner checks apply to every object read,
job creation and inventory response. Opaque inaccessible objects return 404. Database composite
foreign keys constrain tenant ancestry; RLS independently enforces organization scope.

Remote URLs and all content/paths are hostile. One fixed HTTPS API host, DNS address validation
and address-pinned TLS connections prevent private-IP fetching and DNS rebinding. Redirects
fail closed. File bytes never become commands, files on the host, model prompts or executable
configuration. Symlinks/submodules and sensitive paths are excluded before blob fetching.
Metadata entries are bounded by 100,000 files/1 GiB, responses by 16 MiB, supported text by
1 MiB/file, socket timeout by 15 seconds and ingestion checks by a 30-minute deadline.

Known gaps: connection read timeout is per socket operation, not a hard killable wall clock;
GitHub provider compromise is outside this TLS trust boundary; tree provenance relies on the
authenticated provider, while downloaded blobs receive SHA verification. No rate limiter,
OIDC, audit ledger, encrypted source store, secret detector, crash lease, cancellation, fine
grained grants or production deployment is complete. This blocks production approval.
Docker is for local services only, never an asserted hostile-code execution boundary.
