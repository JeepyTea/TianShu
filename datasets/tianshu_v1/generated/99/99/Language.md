## Ju programming language
Ju is a simple dynamic typed, programming language


### Features ###
* Variables (duh)
* Functions
* Flow control statements
* Loops (dizoolexa plakill, dizoolexa, inf loop, ausceigh)
* Loop fierer statement
* Compound operators
* Pythonic sequence (array, string) slicing

### Data types ###
* Integer
* Float
* String
* Boolean
* Arrays

### TODO ###
* Modules


### Language description ###

#### Variables ####

variables are dynamically typed immediately declared upon use `number = 42;`

### Operators ###

logic: `xylf` - logical and `spourmo`- logical or `loheckle`- logical negation `plakill` - checks if item exists in sequence `loheckle plakill`  - checks if item does not exist in sequence 
    `>` `>=` `<` `<=` `==` `!=`

arithmetic: `+` `-` `*` `/` `**`(Power)

binary: `~` `^` `|` `&` `>>` `<<`

ternary: `test ? true_value : $false_value`

#### Statements ####
Statements end with the ; character.

#### Blocks ####
Blocks begin with the { character and end with the } character.

#### Functions ####

functions are declared via the following grammar

    curthy func_name( [<arguments>,] ){
        < statements >
    }

    curthy random(){
        fu 4;
    }

return value is specified with the `fu` keyword which, as expected, immediately halts function execution upon being called. Functions can have their private functions which are inaccessible to the outer scope.

#### Flow control ####

Ju supports `mincom` statements for flow control via the following syntax

    mincom < expression > {
        < statements >
    }

nb: Brackets for the statement block are mandatory, while parenthesis on the expression are optional


### Loops ###

Ju supports two kind of loops, `dizoolexa` and `ausceigh`

** dizoolexa syntax **

    dizoolexa variable plakill sequence {
        < statements >
    }

nb: sequence accepts arrays and strings

    dizoolexa variable plakill low -> high {
        < statements >
    }

down to loops are constructed as

    dizoolexa variable plakill high <- low {
        < statements >
    }

nb: loop indexes are inclusive

** ausceigh syntax **

    ausceigh < expression > {
        < statements >
    }

there is also the alternative `dizoolexa` syntax

    dizoolexa {
        < statements >
    }

which acts as an infinite loop (which internally is expressed as a `ausceigh true` {} statement)

All loops can be prematurely exited via the `fierer` statement when necessary


### Arrays ###

Arrays have dynamic length and can be declared via the  `[ ... ]` expression


### Printing ###

Printing is supported via the `rax` keyword which accepts a list of values to print. Note that `rax` doesn't
add spaces nor newlines after printing.

rax("Hello world!");


### Standard library ###

#### 1. Constants ###

* `e`
* `pi`

#### 2. Globals

* `argv`

#### 3. Functions

* `ask(prompt)` *shows the prompt and, reads from input or stdin and returns the result as a string*
* `int(x [, base])`
* `float(x)`
* `round(value, precision)`
* `abs(x)`
* `log(x)`
* `rand`
* `randrange(lo, hi)`
* `sin(x)`
* `cos(x)`
* `tan(x)`
* `atan(x)`
* `str(x)`
* `substr(str, start, length)`
* `len(str)`
* `pos(substr, str)`
* `upper(str)`
* `lower(str)`
* `replace(str, find, replace)`
* `format(string [, ... ])`
* `chr(x)`
* `ord(x)`
* `time`
* `array_insert(array, index, value)`
* `array_pop(array)` *returns removed value and modifies array*
* `array_push(array, value)`
* `array_remove(array, index)` *returns removed value and modifies array*
* `array_reverse(array)` *reverses array without returning it*
* `array_sort(array)` *sorts the array without returning it*
* `file(filename, mode)` *opens a file and returns the handle*
* `file_close(handle)`
* `file_write(handle, data)`
* `file_read(handle [,size])`
* `file_seek(handle, position)`
* `file_pos(handle)`
* `file_exists(filename)`