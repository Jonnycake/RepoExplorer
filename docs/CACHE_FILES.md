# Description

Cache files in this application are meant to allow the data collection phase to
be avoided.  This can be useful when performing analyses on a separate system
or when changing configurations.  To this end, cache files will contain all the
data we collect in a JSON format and then be compressed using gzip.

# Format

The pre-compression JSON format is as follows:

```
    {
        "authors": {
            <int id>: {
                "full name": <string name>,
                "username": <string username>,
                "email": <string email>
            }
        }
        "commits": {
            <string commit hash>: {
                "author": <int id (references "authors")>,
                "files": [
                    <string path 1>,
                    <string path 2>,
                    ...
                ],
                "date": <commit date - date format: 'MM/dd/YY h:m:s Z'>,
                "impact": {
                    "add": <int number of additions>,
                    "del": <int number of deletions>                }
                }
            }
        },
        "files": {
            <string file path>: {
                "type": <string file type>,
                "content": <string base64 encoded content>,
                "modified": <last modified - date format: 'MM/dd/YY h:m:s Z'>
            }
        }
    }
```
