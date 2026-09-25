# Synthetic work-record fixtures

Everything under this directory is synthetic checker input. It is not a project decision, product result, approval, or completion claim. The fixture runner copies these records into temporary Git repositories and mutates only those temporary copies.

`valid_completion/` starts as a proposed synthetic negative experiment. The runner supplies synthetic commits, test-output metadata, a local mock review report, and status transitions so the checker can exercise its completion contract without treating the fixture as real evidence.
