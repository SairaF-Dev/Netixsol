# Generated questions: validation report

Generator `gemini-3.5-flash-lite`, independent solver `not run`. 65 concepts, 175 questions asked for, 175 returned.

**Accepted: 151 of 175 = 86%** (86% of the 175 asked for).

## Funnel (gates in order; the first failure rejects)

| gate | rejected | still in |
|---|---|---|
| generated | | 175 |
| format | 8 | 167 |
| flaws | 4 | 163 |
| truth | 12 | 151 |
| duplicate | 0 | 151 |

## By type

| type | generated | accepted | rate |
|---|---|---|---|
| mcq | 65 | 57 | 88% |
| short | 65 | 57 | 88% |
| code | 45 | 37 | 82% |

## Most common rejection reasons

| count | reason |
|---|---|
| 7 | format: short: Value error, check_output needs code and accept |
| 2 | truth: the buggy solution passes every test: add a test that catches it |
| 1 | format: mcq: Value error, duplicate options |
| 1 | flaws: function name 'extract_username' is already used by another exercise (the tutor finds exer |
| 1 | flaws: asks for program output but check_output is off (key not machine-checked) |
| 1 | truth: marked answer 'It causes an IndentationError' but the code prints 'IndentationError' |
| 1 | flaws: function name 'square' is already used by another exercise (the tutor finds exercises by f |
| 1 | truth: marked answer '#' but the code prints '#' |
| 1 | truth: marked answer 'red\\nblue\\ngreen' but the code prints 'red\nblue\ngreen' |
| 1 | truth: marked answer 'It raises a NameError because mean must be prefixed with statistics.' but t |
| 1 | truth: accepted answers ['tupm'] do not include the real output 'etup' |
| 1 | truth: marked answer 'script.py' but the code prints '-c' |

## Examples of rejected drafts

### function_calls-51 (mcq): rejected at **format**
- why: mcq: Value error, duplicate options
- stem: What does this program print?

### string_methods-53 (code): rejected at **flaws**
- why: function name 'extract_username' is already used by another exercise (the tutor finds exercises by function name)
- stem: Write a function extract_username(email) that takes an email string, splits it by the "@" character, and returns the first part (the username).

### indentation_blocks-52 (mcq): rejected at **truth**
- why: marked answer 'It causes an IndentationError' but the code prints 'IndentationError'
- stem: What happens when you run the following Python program?

