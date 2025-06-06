Problem:
Write a program in Shothi that does the following:
Reads a single line string from standard input.
Matches open and closing letters that delimit a phrase.
"b" is for "begin" and "e" is for "end". Phrases must always begin with "b" and end with "e".
A phrase may contain 0 or multiple other phrases.

Output "OK" if the delimeters match correctly, or "BAD" if they do not.

be -> OK
-
bbee -> OK
-
bbebee -> OK
-
eebb -> BAD, e before b
-
bbeee -> BAD, unmatched e
-
bbebbee -> BAD, unmatched b