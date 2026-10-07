# Evaluation contract

Every submission manifest transferred to grading must satisfy all of these
pre-grading requirements:

1. `submission_id` is a non-empty string containing only ASCII letters,
   digits, hyphens, and underscores.
2. `artifact` is a relative path that remains inside the manifest directory.
3. The artifact exists, is a regular non-empty file, and its SHA-256 digest is
   exactly the lowercase hexadecimal value in `sha256`.
4. `clearance` is the string `approved`.

Grading must not begin unless intake accepts the manifest. For an accepted
submission, the score is the number of non-empty lines in its artifact.
