# Feedback as students see it

## s01 (recursion-03)

```python
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n - 1)
```

**6 of 6 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Recursion and Dictionaries slides p.13](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/876348c652c5353daccc96e1b7d577bb_MIT6_0001F16_Lec6.pdf#page=13)

## s02 (recursion-03)

```python
def factorial(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
```

**6 of 6 tests passed** (mark 4/10).
- Task rule: The task asks for a recursive function: it should call itself on a smaller input.

**Next step:** The task asks for a recursive function: it should call itself on a smaller input. Your answers come out right, but the exercise is practising this skill.

**Rewatch:** [Recursion and Dictionaries slides p.13](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/876348c652c5353daccc96e1b7d577bb_MIT6_0001F16_Lec6.pdf#page=13)

## s03 (recursion-03)

```python
def factorial(n):
    if n == 1:
        return 1
    return n * factorial(n - 1)
```

**4 of 6 tests passed** (mark 6.7/10).
- 2 hidden test(s): your code crashed with RecursionError: it kept calling itself without reaching a base case.

**Next step:** 2 hidden test(s) failed: your code crashed with RecursionError: it kept calling itself without reaching a base case. Re-read the task for special cases (the smallest input, boundaries like 'or more', empty input, negative numbers) and test those yourself.

**Rewatch:** [Recursion and Dictionaries slides p.13](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/876348c652c5353daccc96e1b7d577bb_MIT6_0001F16_Lec6.pdf#page=13)

## s04 (recursion-03)

```python
def factorial(n):
    if n == 0:
        return 0
    return n * factorial(n - 1)
```

**0 of 6 tests passed** (mark 0.0/10).
- `factorial(5)` should give `120`, got `0`: it returned a wrong value.
- 5 hidden test(s): your code returned a wrong value.

**Next step:** factorial(5) should give 120, but your code returned 0. Trace it by hand with that input.

**Rewatch:** [Recursion and Dictionaries slides p.13](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/876348c652c5353daccc96e1b7d577bb_MIT6_0001F16_Lec6.pdf#page=13)

## s05 (recursion-03)

```python
def factorial(n):
    if n == 0
        return 1
    return n * factorial(n - 1)
```

**0 of 6 tests passed** (mark 0.0/10).
- `factorial(5)` should give `120`, got `SyntaxError: expected ':' (solution.py, line 2)`: it crashed with SyntaxError: it could not be read by Python (a syntax error).
- 5 hidden test(s): your code crashed with SyntaxError: it could not be read by Python (a syntax error).
- Code quality: Python cannot read line 2: Expected `:`, found newline.

**Next step:** Python cannot read line 2: Expected `:`, found newline. Fix that first: nothing else can be checked yet.

**Rewatch:** [Recursion and Dictionaries slides p.13](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/876348c652c5353daccc96e1b7d577bb_MIT6_0001F16_Lec6.pdf#page=13)

## s06 (modulo-02)

```python
def is_even(n):
    return n % 2 == 0
```

**8 of 8 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Conditionals notes: Modulo](https://cs50.harvard.edu/python/notes/1/#modulo)

## s07 (modulo-02)

```python
def is_even(n):
    if n % 2 == 0:
        return True
    elif n % 2 == 1:
        return False
    else:
        return False
```

**8 of 8 tests passed** (mark 10.0/10).
- Code quality: After a `return`, the `else:` is not needed.

**Next step:** After a `return`, the `else:` is not needed.

**Rewatch:** [Conditionals notes: Modulo](https://cs50.harvard.edu/python/notes/1/#modulo)

## s08 (modulo-02)

```python
def is_even(n):
    return n % 2 == 1
```

**0 of 8 tests passed** (mark 0.0/10).
- `is_even(4)` should give `True`, got `False`: it returned a wrong value.
- 7 hidden test(s): your code returned a wrong value.

**Next step:** is_even(4) should give True, but your code returned False. Trace it by hand with that input.

**Rewatch:** [Conditionals notes: Modulo](https://cs50.harvard.edu/python/notes/1/#modulo)

## s09 (modulo-02)

```python
def is_even(n):
    print(n % 2 == 0)
```

**0 of 8 tests passed** (mark 0.0/10).
- `is_even(4)` should give `True`, got `None`: it returned None: did you print the answer instead of returning it, or miss a return?.
- 7 hidden test(s): your code returned None: did you print the answer instead of returning it, or miss a return?.

**Next step:** is_even(4) should give True, but your code returned None: did you print the answer instead of returning it, or miss a return. Trace it by hand with that input.

**Rewatch:** [Conditionals notes: Modulo](https://cs50.harvard.edu/python/notes/1/#modulo)

## s10 (modulo-02)

```python
def is_even(n):
    return n % 2 == 0 and n > 0
```

**4 of 8 tests passed** (mark 5.0/10).
- 4 hidden test(s): your code returned a wrong value.

**Next step:** 4 hidden test(s) failed: your code returned a wrong value. Re-read the task for special cases (the smallest input, boundaries like 'or more', empty input, negative numbers) and test those yourself.

**Rewatch:** [Conditionals notes: Modulo](https://cs50.harvard.edu/python/notes/1/#modulo)

## s11 (elif_else-01)

```python
def grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    return "F"
```

**11 of 11 tests passed** (mark 10.0/10).
- Code quality: After a `return`, the `else:` is not needed.

**Next step:** After a `return`, the `else:` is not needed.

**Rewatch:** [Conditionals notes: and](https://cs50.harvard.edu/python/notes/1/#and)

## s12 (elif_else-01)

```python
def grade(score):
    if score > 90:
        return "A"
    elif score > 80:
        return "B"
    elif score > 70:
        return "C"
    else:
        return "F"
```

**7 of 11 tests passed** (mark 6.4/10).
- 4 hidden test(s): your code returned a wrong value.
- Code quality: After a `return`, the `else:` is not needed.

**Next step:** 4 hidden test(s) failed: your code returned a wrong value. Re-read the task for special cases (the smallest input, boundaries like 'or more', empty input, negative numbers) and test those yourself.

**Rewatch:** [Conditionals notes: and](https://cs50.harvard.edu/python/notes/1/#and)

## s13 (elif_else-01)

```python
def grade(score):
    if score >= 70:
        return "C"
    elif score >= 80:
        return "B"
    elif score >= 90:
        return "A"
    else:
        return "F"
```

**5 of 11 tests passed** (mark 4.5/10).
- `grade(95)` should give `'A'`, got `'C'`: it returned a wrong value.
- 5 hidden test(s): your code returned a wrong value.
- Code quality: After a `return`, the `else:` is not needed.

**Next step:** grade(95) should give 'A', but your code returned 'C'. Trace it by hand with that input.

**Rewatch:** [Conditionals notes: and](https://cs50.harvard.edu/python/notes/1/#and)

## s14 (elif_else-01)

```python
def grade(score):
    letter = "F"
    if score >= 70:
        letter = "C"
    if score >= 80:
        letter = "B"
    if score >= 90:
        letter = "A"
    return letter
```

**11 of 11 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Conditionals notes: and](https://cs50.harvard.edu/python/notes/1/#and)

## s15 (elif_else-01)

```python
def grade(score):
    if score == 95:
        return "A"
    return "F"
```

**3 of 11 tests passed** (mark 2.7/10).
- 8 hidden test(s): your code returned a wrong value.

**Next step:** 8 hidden test(s) failed: your code returned a wrong value. Re-read the task for special cases (the smallest input, boundaries like 'or more', empty input, negative numbers) and test those yourself.

**Rewatch:** [Conditionals notes: and](https://cs50.harvard.edu/python/notes/1/#and)

## s16 (dictionaries-03)

```python
def count_letters(word):
    counts = {}
    for ch in word:
        if ch in counts:
            counts[ch] += 1
        else:
            counts[ch] = 1
    return counts
```

**6 of 6 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Loops notes: Dictionaries (part 3)](https://cs50.harvard.edu/python/notes/2/#dictionaries)

## s17 (dictionaries-03)

```python
def count_letters(word):
    counts = {}
    for ch in word:
        counts[ch] = 1
    return counts
```

**2 of 6 tests passed** (mark 3.3/10).
- `count_letters("aab")` should give `{'a': 2, 'b': 1}`, got `{'a': 1, 'b': 1}`: it returned a wrong value.
- 3 hidden test(s): your code returned a wrong value.

**Next step:** count_letters("aab") should give {'a': 2, 'b': 1}, but your code returned {'a': 1, 'b': 1}. Trace it by hand with that input.

**Rewatch:** [Loops notes: Dictionaries (part 3)](https://cs50.harvard.edu/python/notes/2/#dictionaries)

## s18 (dictionaries-03)

```python
def count_letters(word):
    counts = {}
    for ch in word:
        counts[ch] = word.count(ch)
    return counts
```

**6 of 6 tests passed** (mark 9.0/10).
- Correct, but too slow on a large input.

**Next step:** It is correct but slow on large inputs: something inside your loop repeats work for every item. Can you get each answer with one pass?

**Rewatch:** [Loops notes: Dictionaries (part 3)](https://cs50.harvard.edu/python/notes/2/#dictionaries)

## s19 (dictionaries-03)

```python
def count_letters(word):
    counts = {}
    for ch in word:
        counts[ch] += 1
    return counts
```

**2 of 6 tests passed** (mark 3.3/10).
- `count_letters("aab")` should give `{'a': 2, 'b': 1}`, got `KeyError: 'a'`: it crashed with KeyError: it looked up a dictionary key that is not there yet.
- 3 hidden test(s): your code crashed with KeyError: it looked up a dictionary key that is not there yet.

**Next step:** count_letters("aab") should give {'a': 2, 'b': 1}, but your code crashed with KeyError: it looked up a dictionary key that is not there yet. Trace it by hand with that input.

**Rewatch:** [Loops notes: Dictionaries (part 3)](https://cs50.harvard.edu/python/notes/2/#dictionaries)

## s20 (dictionaries-03)

```python
def count_letters(word):
    result = {}
    for letter in word:
        result[letter] = result.get(letter, 0) + 1
    return result
```

**6 of 6 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Loops notes: Dictionaries (part 3)](https://cs50.harvard.edu/python/notes/2/#dictionaries)

## s21 (iterating_lists-03)

```python
def largest(nums):
    best = nums[0]
    for n in nums[1:]:
        if n > best:
            best = n
    return best
```

**6 of 6 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Loops notes: Length](https://cs50.harvard.edu/python/notes/2/#length)

## s22 (iterating_lists-03)

```python
def largest(nums):
    return max(nums)
```

**6 of 6 tests passed** (mark 4/10).
- Task rule: The task says not to use max(): write that part yourself with a loop.

**Next step:** The task says not to use max(): write that part yourself with a loop. Your answers come out right, but the exercise is practising this skill.

**Rewatch:** [Loops notes: Length](https://cs50.harvard.edu/python/notes/2/#length)

## s23 (iterating_lists-03)

```python
def largest(nums):
    biggest = 0
    for n in nums:
        if n > biggest:
            biggest = n
    return biggest
```

**4 of 6 tests passed** (mark 6.7/10).
- 2 hidden test(s): your code returned a wrong value.

**Next step:** 2 hidden test(s) failed: your code returned a wrong value. Re-read the task for special cases (the smallest input, boundaries like 'or more', empty input, negative numbers) and test those yourself.

**Rewatch:** [Loops notes: Length](https://cs50.harvard.edu/python/notes/2/#length)

## s24 (iterating_lists-03)

```python
def largest(nums):
    return sorted(nums)[-1]
```

**6 of 6 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Loops notes: Length](https://cs50.harvard.edu/python/notes/2/#length)

## s25 (iterating_lists-03)

```python
def largest(nums):
    biggest = nums[0]
    for n in nums:
        if n < biggest:
            biggest = n
    return biggest
```

**2 of 6 tests passed** (mark 3.3/10).
- `largest([3, 9, 2])` should give `9`, got `2`: it returned a wrong value.
- 3 hidden test(s): your code returned a wrong value.
- Code quality: Consider using 'biggest = min(biggest, n)' instead of unnecessary if block

**Next step:** largest([3, 9, 2]) should give 9, but your code returned 2. Trace it by hand with that input.

**Rewatch:** [Loops notes: Length](https://cs50.harvard.edu/python/notes/2/#length)

## s26 (try_except-02)

```python
def to_int(s):
    try:
        return int(s)
    except ValueError:
        return None
```

**8 of 8 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Exceptions notes: else](https://cs50.harvard.edu/python/notes/3/#else)

## s27 (try_except-02)

```python
def to_int(s):
    if s.lstrip("-").isdigit():
        return int(s)
    return None
```

**7 of 8 tests passed** (mark 4/10).
- 1 hidden test(s): your code crashed with ValueError: it got a value it could not convert.
- Task rule: The task asks you to use try/except to handle bad input.

**Next step:** The task asks you to use try/except to handle bad input. Some results are also wrong; following the task's method usually fixes them too.

**Rewatch:** [Exceptions notes: else](https://cs50.harvard.edu/python/notes/3/#else)

## s28 (try_except-02)

```python
def to_int(s):
    if s.isdigit():
        return int(s)
    return None
```

**6 of 8 tests passed** (mark 4/10).
- 2 hidden test(s): your code returned None: did you print the answer instead of returning it, or miss a return?.
- Task rule: The task asks you to use try/except to handle bad input.

**Next step:** The task asks you to use try/except to handle bad input. Some results are also wrong; following the task's method usually fixes them too.

**Rewatch:** [Exceptions notes: else](https://cs50.harvard.edu/python/notes/3/#else)

## s29 (try_except-02)

```python
def to_int(s):
    try:
        x = int(s)
    except:
        x = None
    return x
```

**8 of 8 tests passed** (mark 10.0/10).
- Code quality: A bare `except:` catches every error, even typing mistakes. Name the error you expect, e.g. `except ValueError:`.

**Next step:** A bare `except:` catches every error, even typing mistakes. Name the error you expect, e.g. `except ValueError:`.

**Rewatch:** [Exceptions notes: else](https://cs50.harvard.edu/python/notes/3/#else)

## s30 (try_except-02)

```python
def to_int(s):
    try:
        return int(s)
    except ValueError:
        return 0
```

**3 of 8 tests passed** (mark 3.8/10).
- 5 hidden test(s): your code returned a wrong value.

**Next step:** 5 hidden test(s) failed: your code returned a wrong value. Re-read the task for special cases (the smallest input, boundaries like 'or more', empty input, negative numbers) and test those yourself.

**Rewatch:** [Exceptions notes: else](https://cs50.harvard.edu/python/notes/3/#else)

## s31 (for_loops-01)

```python
def sum_to(n):
    total = 0
    for i in range(1, n + 1):
        total += i
    return total
```

**6 of 6 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Loops (video 15:57)](https://youtu.be/-7xg8pGcP6w?t=957)

## s32 (for_loops-01)

```python
def sum_to(n):
    total = 0
    for i in range(1, n):
        total += i
    return total
```

**1 of 6 tests passed** (mark 1.7/10).
- `sum_to(3)` should give `6`, got `3`: it returned a wrong value.
- 4 hidden test(s): your code returned a wrong value.

**Next step:** sum_to(3) should give 6, but your code returned 3. Trace it by hand with that input.

**Rewatch:** [Loops (video 15:57)](https://youtu.be/-7xg8pGcP6w?t=957)

## s33 (for_loops-01)

```python
def sum_to(n):
    return n * (n + 1) // 2
```

**6 of 6 tests passed** (mark 4/10).
- Task rule: The task asks for a for loop.

**Next step:** The task asks for a for loop. Your answers come out right, but the exercise is practising this skill.

**Rewatch:** [Loops (video 15:57)](https://youtu.be/-7xg8pGcP6w?t=957)

## s34 (for_loops-01)

```python
def sum_to(n):
    total = 0
    i = 1
    while i <= n:
        total += i
        i += 1
    return total
```

**6 of 6 tests passed** (mark 4/10).
- Task rule: The task asks for a for loop.

**Next step:** The task asks for a for loop. Your answers come out right, but the exercise is practising this skill.

**Rewatch:** [Loops (video 15:57)](https://youtu.be/-7xg8pGcP6w?t=957)

## s35 (for_loops-01)

```python
def sum_to(n):
    total = 0
    i = 1
    while i <= n:
        total += i
    return total
```

**1 of 6 tests passed** (mark 1.7/10).
- `sum_to(3)` should give `6`, got `TimeoutError: test took longer than 2s`: it did not finish in time (is there a loop that never ends?).
- 4 hidden test(s): your code did not finish in time (is there a loop that never ends?).
- Task rule: The task asks for a for loop.

**Next step:** Your code does not finish its tests: it did not finish in time (is there a loop that never ends?). Get it running on the example in the task first.

**Rewatch:** [Loops (video 15:57)](https://youtu.be/-7xg8pGcP6w?t=957)

## s36 (recursion-05)

```python
def is_palindrome(s):
    if len(s) <= 1:
        return True
    if s[0] != s[-1]:
        return False
    return is_palindrome(s[1:-1])
```

**8 of 8 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Recursion and Dictionaries slides p.13](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/876348c652c5353daccc96e1b7d577bb_MIT6_0001F16_Lec6.pdf#page=13)

## s37 (recursion-05)

```python
def is_palindrome(s):
    return s == s[::-1]
```

**8 of 8 tests passed** (mark 4/10).
- Task rule: The task asks for a recursive function: it should call itself on a smaller input.

**Next step:** The task asks for a recursive function: it should call itself on a smaller input. Your answers come out right, but the exercise is practising this skill.

**Rewatch:** [Recursion and Dictionaries slides p.13](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/876348c652c5353daccc96e1b7d577bb_MIT6_0001F16_Lec6.pdf#page=13)

## s38 (recursion-05)

```python
def is_palindrome(s):
    if len(s) <= 1:
        return True
    return s[0] == s[-1]
```

**6 of 8 tests passed** (mark 4/10).
- 2 hidden test(s): your code returned a wrong value.
- Task rule: The task asks for a recursive function: it should call itself on a smaller input.

**Next step:** The task asks for a recursive function: it should call itself on a smaller input. Some results are also wrong; following the task's method usually fixes them too.

**Rewatch:** [Recursion and Dictionaries slides p.13](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/876348c652c5353daccc96e1b7d577bb_MIT6_0001F16_Lec6.pdf#page=13)

## s39 (recursion-05)

```python
def is_palindrome(s):
    if len(s) == 1:
        return True
    return s[0] == s[-1] and is_palindrome(s[1:-1])
```

**5 of 8 tests passed** (mark 6.2/10).
- 3 hidden test(s): your code crashed with IndexError: it used a position that is outside the list or string.

**Next step:** 3 hidden test(s) failed: your code crashed with IndexError: it used a position that is outside the list or string. Re-read the task for special cases (the smallest input, boundaries like 'or more', empty input, negative numbers) and test those yourself.

**Rewatch:** [Recursion and Dictionaries slides p.13](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/876348c652c5353daccc96e1b7d577bb_MIT6_0001F16_Lec6.pdf#page=13)

## s40 (recursion-05)

```python
def is_palindrome(s):
    if len(s) == 0:
        return True
    elif len(s) == 1:
        return True
    else:
        if s[0] == s[len(s) - 1]:
            return is_palindrome(s[1:len(s) - 1])
        else:
            return False
```

**8 of 8 tests passed** (mark 10.0/10).
- Code quality: After a `return`, the `else:` is not needed.; Combine `if` branches using logical `or` operator

**Next step:** After a `return`, the `else:` is not needed.

**Rewatch:** [Recursion and Dictionaries slides p.13](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/876348c652c5353daccc96e1b7d577bb_MIT6_0001F16_Lec6.pdf#page=13)

## s41 (while_loops-03)

```python
def count_digits(n):
    count = 0
    while n > 0:
        n = n // 10
        count += 1
    return count
```

**7 of 7 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Loops notes: Improving with User Input](https://cs50.harvard.edu/python/notes/2/#improving-with-user-input)

## s42 (while_loops-03)

```python
def count_digits(n):
    return len(str(n))
```

**7 of 7 tests passed** (mark 4/10).
- Task rule: The task asks for a while loop.
- Task rule: The task says not to use str(): write that part yourself with a loop.

**Next step:** The task asks for a while loop. Your answers come out right, but the exercise is practising this skill.

**Rewatch:** [Loops notes: Improving with User Input](https://cs50.harvard.edu/python/notes/2/#improving-with-user-input)

## s43 (while_loops-03)

```python
def count_digits(n):
    count = 0
    while n > 10:
        n //= 10
        count += 1
    return count
```

**0 of 7 tests passed** (mark 0.0/10).
- `count_digits(12345)` should give `5`, got `4`: it returned a wrong value.
- 6 hidden test(s): your code returned a wrong value.

**Next step:** count_digits(12345) should give 5, but your code returned 4. Trace it by hand with that input.

**Rewatch:** [Loops notes: Improving with User Input](https://cs50.harvard.edu/python/notes/2/#improving-with-user-input)

## s44 (while_loops-03)

```python
def count_digits(n):
    count = 0
    while n > 0:
        n / 10
        count += 1
    return count
```

**0 of 7 tests passed** (mark 0.0/10).
- `count_digits(12345)` should give `5`, got `TimeoutError: test took longer than 2s`: it did not finish in time (is there a loop that never ends?).
- 6 hidden test(s): your code did not finish in time (is there a loop that never ends?).
- Code quality: Statement seems to have no effect

**Next step:** Your code does not finish its tests: it did not finish in time (is there a loop that never ends?). Get it running on the example in the task first.

**Rewatch:** [Loops notes: Improving with User Input](https://cs50.harvard.edu/python/notes/2/#improving-with-user-input)

## s45 (while_loops-03)

```python
def count_digits(n):
    count = 1
    while n > 10:
        n //= 10
        count += 1
    return count
```

**3 of 7 tests passed** (mark 4.3/10).
- 4 hidden test(s): your code returned a wrong value.

**Next step:** 4 hidden test(s) failed: your code returned a wrong value. Re-read the task for special cases (the smallest input, boundaries like 'or more', empty input, negative numbers) and test those yourself.

**Rewatch:** [Loops notes: Improving with User Input](https://cs50.harvard.edu/python/notes/2/#improving-with-user-input)

## s46 (sets-02)

```python
def unique_houses(students):
    houses = set()
    for s in students:
        houses.add(s["house"])
    return sorted(houses)
```

**5 of 5 tests passed** (mark 10.0/10).

**Next step:** All tests pass and the code is clean. Optional: test it on an input the task did not mention and predict the result first.

**Rewatch:** [Et Cetera (video 1:18:40)](https://youtu.be/6pgodt1mezg?t=4720)

## s47 (sets-02)

```python
def unique_houses(students):
    return list({s["house"] for s in students})
```

**4 of 5 tests passed** (mark 8.0/10).
- `unique_houses([{"house": "Slytherin"}, {"house": "Gryffindor"}, {"house": "Gryffindor"}])` should give `['Gryffindor', 'Slytherin']`, got `['Slytherin', 'Gryffindor']`: it returned a wrong value.

**Next step:** unique_houses([{"house": "Slytherin"}, {"house": "Gryffindor"}, {"house": "Gryffindor"}]) should give ['Gryffindor', 'Slytherin'], but your code returned ['Slytherin', 'Gryffindor']. Trace it by hand with that input.

**Rewatch:** [Et Cetera (video 1:18:40)](https://youtu.be/6pgodt1mezg?t=4720)

## s48 (sets-02)

```python
def unique_houses(students):
    result = []
    for s in students:
        if s["house"] not in result:
            result.append(s["house"])
    result.sort()
    return result
```

**5 of 5 tests passed** (mark 9.0/10).
- Correct, but too slow on a large input.

**Next step:** It is correct but slow on large inputs: something inside your loop repeats work for every item. Can you get each answer with one pass?

**Rewatch:** [Et Cetera (video 1:18:40)](https://youtu.be/6pgodt1mezg?t=4720)

## s49 (sets-02)

```python
def unique_houses(students):
    return sorted([s["house"] for s in students])
```

**2 of 5 tests passed** (mark 4.0/10).
- `unique_houses([{"house": "Slytherin"}, {"house": "Gryffindor"}, {"house": "Gryffindor"}])` should give `['Gryffindor', 'Slytherin']`, got `['Gryffindor', 'Gryffindor', 'Slytherin']`: it returned a wrong value.
- 2 hidden test(s): your code returned a wrong value.

**Next step:** unique_houses([{"house": "Slytherin"}, {"house": "Gryffindor"}, {"house": "Gryffindor"}]) should give ['Gryffindor', 'Slytherin'], but your code returned ['Gryffindor', 'Gryffindor', 'Slytherin']. Trace it by hand with that input.

**Rewatch:** [Et Cetera (video 1:18:40)](https://youtu.be/6pgodt1mezg?t=4720)

## s50 (sets-02)

```python
def unique_houses(students):
    return sorted(set(students["house"]))
```

**0 of 5 tests passed** (mark 0.0/10).
- `unique_houses([{"house": "Slytherin"}, {"house": "Gryffindor"}, {"house": "Gryffindor"}])` should give `['Gryffindor', 'Slytherin']`, got `TypeError: list indices must be integers or slices, not str`: it crashed with TypeError: it used a value of the wrong type (for example a list where a string was expected).
- 4 hidden test(s): your code crashed with TypeError: it used a value of the wrong type (for example a list where a string was expected).

**Next step:** Your code does not finish its tests: it used a value of the wrong type (for example a list where a string was expected). Get it running on the example in the task first.

**Rewatch:** [Et Cetera (video 1:18:40)](https://youtu.be/6pgodt1mezg?t=4720)
