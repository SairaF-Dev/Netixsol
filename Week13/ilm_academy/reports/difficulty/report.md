# Difficulty calibration: LLM vs IRT

`gemini-3.5-flash-lite` predicted the share of beginners answering correctly for 201 bank questions (without seeing the author's label). Compared on 183 questions with 50+ simulated answers (planted bad questions left out).

| difficulty source | Spearman with IRT b (measured) | simulation only: with the hidden true b |
|---|---|---|
| author's 1-5 guess | 0.561 | 0.75 |
| LLM prediction | 0.326 | 0.326 |
| LLM + author (mean rank) | 0.516 | |
| IRT itself | 1 | 0.707 |

LLM vs author: 0.533. Mean predicted correct 74.2% vs observed 51.7%.

By type (Spearman with IRT b): code LLM 0.249 / author 0.699, mcq LLM 0.07 / author 0.571, short LLM 0.733 / author 0.876

**Caveat.** The simulator makes true difficulty = the author's guess + noise, so these numbers favour the author by construction. They show the pipeline works; only real students can say whether the LLM or the author judges difficulty better.

## Decisions

| decision | questions |
|---|---|
| keep | 142 |
| relabel | 40 |
| unmeasured | 30 |
| retire | 13 |

Retired questions that were planted bad: 12 of 12 planted bad that were measured.

## Retire

| question | a | b | reason |
|---|---|---|---|
| tuples_unpacking-01 | -0.10 | 5.46 | negative discrimination: strong students do WORSE |
| break_continue-02 | -0.09 | 8.25 | negative discrimination: strong students do WORSE |
| nested_loops-01 | 0.01 | -27.93 | weak discrimination: strong and weak students do about the same |
| floats-04 | 0.07 | 1.84 | weak discrimination: strong and weak students do about the same |
| user_input-01 | 0.11 | -3.80 | weak discrimination: strong and weak students do about the same |
| arithmetic_operators-01 | 0.12 | -4.26 | weak discrimination: strong and weak students do about the same |
| range_function-02 | 0.14 | -3.45 | weak discrimination: strong and weak students do about the same |
| packages_pip-01 | 0.15 | -0.18 | weak discrimination: strong and weak students do about the same |
| indentation_blocks-02 | 0.17 | -1.57 | weak discrimination: strong and weak students do about the same |
| function_calls-01 | 0.18 | -2.34 | weak discrimination: strong and weak students do about the same |
| type_hints-03 | 0.19 | -2.14 | weak discrimination: strong and weak students do about the same |
| dict_comprehensions-02 | 0.26 | 1.45 | weak discrimination: strong and weak students do about the same |
| floats-02 | 0.27 | 1.73 | weak discrimination: strong and weak students do about the same |

## Relabel (author's level is 2+ away from the measured level)

| question | author | measured | LLM % correct | LLM's reason |
|---|---|---|---|---|
| variables-02 | 3 | 1 | 55 | Variables hold values, not references to other variables in a reactive way; this is a classic beginner pitfall. |
| strings-04 | 1 | 3 | 70 | Writing a simple function using f-strings or concatenation is standard practice. |
| function_calls-02 | 4 | 2 | 50 | Printing the return value of print() yields None, which is surprising to beginners. |
| user_input-03 | 3 | 5 | 70 | Explaining type casting (int()) is a staple exercise in CS50P. |
| arithmetic_operators-03 | 2 | 5 | 95 | Basic math function with parameters and return value is straightforward for beginners. |
| type_conversion-04 | 2 | 5 | 85 | Combining input/string conversion into an addition task is a classic beginner exercise. |
| defining_functions-03 | 1 | 5 | 95 | Writing a simple single-parameter function is universally practiced. |
| parameters-01 | 2 | 4 | 75 | Default arguments are clear, though tracing multiple calls requires careful reading. |
| boolean_expressions-01 | 3 | 1 |  |  |
| boolean_expressions-02 | 4 | 2 |  |  |
| logical_operators-02 | 5 | 3 |  |  |
| logical_operators-03 | 2 | 4 | 65 | Students often struggle with combining inequalities or inclusive bounds using 'and'. |
| match_statement-03 | 2 | 4 | 70 | Writing a match function requires remembering syntax. |
| while_loops-03 | 3 | 5 | 45 | Arithmetic loop for digits is tricky for beginners. |
| for_loops-03 | 3 | 1 | 55 | Variable reassignment instead of accumulation trips up many. |
| iterating_lists-01 | 2 | 4 | 75 | Standard filtering loop pattern. |
| nested_data-02 | 3 | 5 | 65 | Iterating over a list of dicts and conditionally building a result list takes a few steps. |
| nested_data-03 | 2 | 4 | 70 | Negative indexing combined with nested dictionary access can confuse some. |
| slicing-03 | 2 | 4 | 80 | Using slice notation [1:-1] for removing ends is a clean, standard idiom. |
| slicing-04 | 3 | 5 | 75 | Negative slicing from the end [-2:] is well-grasped after examples. |
| apis_json-01 | 3 | 1 | 88 | json.loads parses JSON dict into Python dict; age is int 36. |
| apis_json-03 | 3 | 5 | 75 | List comprehension over nested dictionaries is standard practice. |
| own_modules-03 | 2 | 4 | 78 | Requires writing a basic import and function call statement. |
| pytest_testing-02 | 4 | 2 | 82 | Testing even/odd, zero, and negative values covers edge cases best. |
| pytest_testing-04 | 2 | 4 | 75 | Conceptual explanation of robustness and edge cases. |
| raising_exceptions-01 | 3 | 5 | 75 | Standard conditional check combined with raising an exception is straightforward. |
| properties_decorators-01 | 4 | 2 | 70 | Students who understand properties recognize the setter raises a ValueError for invalid input. |
| operator_overloading-01 | 3 | 1 | 65 | Students often struggle to follow custom dunder methods like __add__. |
| docstrings-03 | 3 | 5 | 80 | Well-discussed distinction in documentation lessons. |
| argparse_module-02 | 2 | 4 | 90 | Main selling point of argparse over sys.argv. |
| argparse_module-03 | 3 | 5 | 55 | Syntax for passing a list to parse_args() trips beginners up. |
| args_kwargs-01 | 3 | 1 | 80 | Direct demonstration of args as tuple and kwargs as dict. |
| args_kwargs-02 | 3 | 5 | 85 | Standard loop over *args. |
| lambda_functions-02 | 2 | 5 | 65 | Students often get confused by syntax variations of lambdas. |
| lambda_functions-03 | 3 | 5 | 50 | Combining sorted(), key parameter, and lambda is tricky for beginners. |
| list_comprehensions-02 | 2 | 4 | 85 | Straightforward application of list comprehensions with string methods. |
| enumerate_function-03 | 3 | 5 | 90 | Enumerate is heavily emphasized as the pythonic way. |
| generators-01 | 4 | 1 | 60 | Understanding next() and generator state is moderately tricky. |
| recursion-03 | 2 | 4 | 85 | Factorial is the canonical introductory recursive function. |
| recursion-04 | 3 | 5 | 70 | Fibonacci is standard, though slightly harder than factorial due to two recursive calls. |
