# Dependency security review — 2026-10-02

## Result

`npm audit --json` against the committed `web/package-lock.json` reported 24 advisories: 1 critical, 16 high, 6 moderate, and 1 low. The direct dependency findings include `next@16.2.6` (critical aggregate), `react-server-dom-webpack@19.2.6` (high), `@cloudflare/vite-plugin@1.37.1` (high), `vinext@0.0.50` (high), `vite@8.0.13` (high), and `wrangler@4.92.0` (high). Remaining findings are transitive packages.

The reported critical includes a Next.js Windows-hosted server RCE affecting versions below 16.3.3 ([GHSA-p293-qw3h-jr36](https://github.com/advisories/GHSA-p293-qw3h-jr36)); the audit also flags a `next/og` RCE below 16.3.6 ([GHSA-vcvr-r3jv-pc5j](https://github.com/advisories/GHSA-vcvr-r3jv-pc5j)). The application build uses Vinext/Vite, the accepted temporary runtime is Linux, and a source search found no `next/og`/`ImageResponse`, middleware/proxy file, or Server Action marker. This narrows apparent applicability but is not a full security proof. React Server Functions dependencies also have a high-severity DoS advisory for affected versions below 19.2.8 ([GHSA-wx67-qw84-cm4g](https://github.com/advisories/GHSA-wx67-qw84-cm4g)).

## Handling

- `package.json`, `package-lock.json`, and `pnpm-lock.yaml` remain unchanged from the certified source package.
- No `npm audit fix` or dependency upgrade was applied: that would change the accepted runtime dependency set and require compatibility, build, and deployment regression beyond a backup-only operation. In particular, audit-suggested Vinext remediation crosses a major/prerelease boundary.
- `npm ci` completed from the lockfile; `npm test` passed (production build plus 8 rendered-HTML tests). This does not clear the advisories.
- Do not use this branch as a security-cleared production deployment. Track dependency remediation as a separate, explicitly tested change before exposure on a Windows-hosted Next server or promotion beyond this candidate.

`DEPENDENCY_SECURITY_STATUS = KNOWN_ADVISORIES_NOT_REMEDIATED`
