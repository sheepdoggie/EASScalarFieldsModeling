# Job Bundle Policy

For delegated modeling, the operator should provide configuration only.

Allowed files:

```text
SUITE.json
overlays/*.json
README_RUN_COMMAND.txt
EXPECTED_FRAMEWORK.json
```

Forbidden files:

```text
*.py
*.sh
*.bat
*.ps1
framework/*.zip
run_all_*.sh
custom runners
custom adapters
custom readouts
```

The installed canonical framework should be the only executable system.
