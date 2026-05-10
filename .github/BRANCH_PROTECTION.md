# Branch Protection

GitHub required checks are repository settings, not files in this repository.
After the first CI run appears, protect the merge target branch and require
these status checks before merging:

- `Ruff`
- `Mypy`
- `Coverage`
- `Compatibility / Python 3.10`
- `Compatibility / Python 3.11`
- `Compatibility / Python 3.12`
- `Compatibility / Python 3.13`
- `Compatibility / Python 3.14`

Recommended settings:

- Require a pull request before merging.
- Require status checks to pass before merging.
- Require branches to be up to date before merging.
- Include administrators if this repository should enforce the same gate for
  maintainers.

Codecov is configured with OIDC in `.github/workflows/ci.yml`, so a
`CODECOV_TOKEN` secret is not required when Codecov OIDC is enabled for the
repository. If the repository uses token-based uploads instead, replace
`use_oidc: true` with `token: ${{ secrets.CODECOV_TOKEN }}` and add that secret
in GitHub.
