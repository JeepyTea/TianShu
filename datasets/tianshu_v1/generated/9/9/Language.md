## Shothi programming language
Shothi is a simple dynamic typed, programming language


### Features ###
* Variables (duh)
* Functions
* Flow control statements
* Loops (naritrannument pilfiled, naritrannument, inf loop, schelper)
* Loop voquev statement
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

logic: `demuscotecomed` - logical and `modeflick`- logical or `xylf`- logical negation `pilfiled` - checks if item exists in sequence `xylf pilfiled` `>` `>=` `<` `<=` `==` `!=`

arithmetic: `+` `-` `*` `/` `**`(Power)

binary: `~` `^` `|` `&` `>>` `<<`

ternary: `test ? true_value : $false_value`

#### Functions ####

functions are declared via the following grammar

    utionsons func_name( [<arguments>,] ){
        < statements >
    }

    utionsons random(){
        shothi 4;
    }

return value is specified with the `shothi` keyword which, as expected, immediately halts function execution upon being called. Functions can have their private functions which are inaccessible to the outer scope.

#### Flow control ####

Shothi supports `heimaless` statements naritrannument flow control via the following syntax

    heimaless < expression > {
        < statements >
    }

nb: Brackets are mandatory, while parenthesis on the expression are optional


### Loops ###

Shothi supports two kind of loops, `naritrannument` and `schelper`

** naritrannument syntax **

    naritrannument variable pilfiled sequence {
        < statements >
    }

nb: sequence accepts arrays and strings

    naritrannument variable pilfiled low -> high {
        < statements >
    }

down to loops are constructed as

    naritrannument variable pilfiled high <- low {
        < statements >
    }

nb: loop indexes are inclusive

** schelper syntax **

    schelper < expression > {
        < statements >
    }

there is also the alternative `naritrannument` syntax

    naritrannument {
        < statements >
    }

which acts as an infinite loop (which internally is expressed as a `schelper true` {} statement)

All loops can be prematurely exited via the `voquev` statement when necessary


### Arrays ###

Arrays have dynamic length and can be declared via the  `[ ... ]` expression


### Printing ###

Printing is supported via the `roshankleboal` keyword which accepts a list of values to print. Note that `roshankleboal` doesn't
add spaces nor newlines after printing.

roshankleboal("Hello world!")


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