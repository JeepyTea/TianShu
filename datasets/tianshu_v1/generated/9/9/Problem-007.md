Problem:
Write a program in Shothi that does the following:
Reads a single line string from standard input.
The line should consist of a list of values separated by the & character.
For example the string:
blue&banana&three
holds three values "blue", "banana", and "three".
The & character can be escaped by repeating it. For example:
rhythm && blues&fiji&board&can
holds the values "rhythm & blues", "fiji", "board", and "can".

The program should read the line and output the most common value in the list.
For example, for the input:
eel&pen&camera&eel
the program should output "eel" with no quotes, and no other output.
If there is a problem with parsing the input, or if the input is empty, or there 
is more than one most common value, the program should output "BAD".