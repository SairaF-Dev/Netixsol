# Generated questions: validation report

Generator `gemini-3.5-flash-lite`, independent solver `not run`. 65 concepts, 175 questions asked for, 175 returned.

**Accepted: 143 of 175 = 82%** (82% of the 175 asked for).

## Funnel (gates in order; the first failure rejects)

| gate | rejected | still in |
|---|---|---|
| generated | | 175 |
| format | 11 | 164 |
| flaws | 6 | 158 |
| truth | 14 | 144 |
| duplicate | 1 | 143 |

## By type

| type | generated | accepted | rate |
|---|---|---|---|
| mcq | 65 | 53 | 82% |
| short | 65 | 54 | 83% |
| code | 45 | 36 | 80% |

## Most common rejection reasons

| count | reason |
|---|---|
| 9 | format: short: Value error, check_output needs code and accept |
| 4 | truth: the buggy solution passes every test: add a test that catches it |
| 1 | format: mcq: Value error, duplicate options |
| 1 | truth: marked answer 'What is your name? Bob\nhello, Bob' but the code prints 'What is your name? |
| 1 | flaws: function name 'min_max' is already used by another exercise (the tutor finds exercises by  |
| 1 | flaws: asks for program output but check_output is off (key not machine-checked) |
| 1 | flaws: misconceptions missing, too short or repeated |
| 1 | duplicate: #.# similar to range_function-# |
| 1 | truth: marked answer '# red' but the code prints '# red\nIndexError' |
| 1 | flaws: the correct option is clearly the longest (guessable) |
| 1 | truth: accepted answers ['Unknown'] do not include the real output 'The Beatles' |
| 1 | truth: marked answer 'It raises an AssertionError' but the code prints 'AssertionError' |

## Examples of rejected drafts

### program_basics-51 (mcq): rejected at **format**
- why: mcq: Value error, duplicate options
- stem: What does this program print?

### user_input-51 (mcq): rejected at **truth**
- why: marked answer 'What is your name? Bob\nhello, Bob' but the code prints 'What is your name? EOFError'
- stem: Examine the following code snippet. If the user runs this program and types Bob when prompted, what is the exact output of the program?

### return_values-53 (code): rejected at **flaws**
- why: function name 'min_max' is already used by another exercise (the tutor finds exercises by function name)
- stem: Write a function named min_max(numbers) that takes a list of numbers and returns a tuple containing the minimum value and the maximum value from that list, in that order (e.g., min_max([1, 5, 2]) returns (1, 5)).

### range_function-52 (short): rejected at **duplicate**
- why: 0.85 similar to range_function-03
- stem: Type exactly what this program prints.

