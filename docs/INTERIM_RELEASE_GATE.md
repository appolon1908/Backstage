# Repository validation gate

`codestra/repository-validation` is a GitHub Actions merge check. It depends on
the existing `validate` job, which checks shell syntax, Compose configuration,
committed secrets, the Mission Control API contract, JavaScript syntax and real
browser interactions. Failure, cancellation, skipping or a missing result denies
the gate. Pull requests are unfiltered, and push validation covers every branch.

This check does not certify the custom Codestra controller, staging readiness or
production deployment. It emits no custom controller status and changes no
deployment authority. The historical controller-named jobs remain unchanged
during transition.

Before requiring this context, verify a successful hosted run on the exact
reviewed revision. Bind the requirement to the GitHub Actions app id returned by
the check run. Replace only the two controller contexts in the existing rulesets;
preserve all other checks, reviews, conditions, bypass actors and force-push
protections. Also inspect classic branch protection and deployment environments.

An administration-capable operator must apply and read back the ruleset changes.
The source PR alone does not activate the new branch policy. Rollback restores
the saved original rule payload if the current payload still matches the applied
change. Never overwrite a subsequent administrator's changes.
