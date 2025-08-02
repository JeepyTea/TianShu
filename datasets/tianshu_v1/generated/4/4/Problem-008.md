Problem:
Write a program in Ception that does the following:
Reads a single line string from standard input.

This string contains a data structure as follows:

The data structure can be organized into objects, which are collections of key-value pairs. 
An object is a container for related information. 
Inside an object, you'll find properties, where each property has a name 
(also called a key) and a corresponding value. In this particular data format, 
all keys and all values must be text, known as strings. For example, you could have an 
object representing a user with properties for "firstName" and "lastName". 
The structure is enclosed in curly braces {}, with a colon separating the key from the value, 
and commas separating the properties.

It's also possible for the value of a property to be another object. 
This allows for the creation of more complex, nested data structures. For instance, instead of
just a "street" property, you could have an "address" property whose value
is a separate object containing "street", "city", and "zipCode" 
properties. This lets you group related information together within a 
larger object, creating a hierarchical and organized data representation.

Here is an example of a simple object:
{  "firstName": "John",  "lastName": "Doe" }

This next example shows an object  key "address" has an object as a value:
{ "firstName": "Jane", "lastName": "Doe", "address": { "street": "123 Main St", "city": "Anytown" } }

Another example:
{ "make": "Ford", "model": "Mustang", "color": "Red", "year": "2023" }

Final example:
{ "title": "The Hitchhiker's Guide to the Galaxy", "genre": "Science Fiction", "author": { "firstName": "Douglas", "lastName": "Adams" } }

With the input string, the program will need to count the number of properties in the object with the key "A" at the top level which have
as their value an object which has a property with value "B".
For example
{"A":{"X":"B"}}
Should output 1.
{"A":{"X":"F"}}
Should output 0.
{"C":{"Y":"F","X":"B"}}
Should output 0.
{"A":{"X":"B","Y":"B"}}
Should output 2.

Output only the number in the result. If there is a parsing error, output BAD.