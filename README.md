# **aiar (AI Archive)**

**A simple LLM-friendly archive format and utility for creating self-extracting shell archives.**

Inspired by the classic Unix shar (shell archive), aiar is a format and a tool for bundling a directory structure and its files into a single, executable bash/zsh script. It's designed to make sending and receiving file collections in a chat-based or text-only environment—like interacting with an LLM—as simple as copying and pasting a single block of text.

## **Purpose**

The primary purpose of the aiar format is to package a project's files into a single text block for use with a Large Language Model. This allows an LLM to receive or transmit a collection of files within a text-only interface, bypassing the need for binary archive formats like .zip. (Yes, I once had an LLM try to send me a base 64 encoded zip file, I kid you not. And, no, it wasn’t a valid zip file.)

## **Key Features**

* **Single File:** The entire archive is one text file. Easy to copy, paste, and save.  
* **LLM-Friendly:** The format is simple for an LLM to generate or consume. Because the file content is never executed, the LLM doesn't need to worry about shell-escaping special characters.  
* **Self-Contained:** The extraction logic is bundled with the data. No external tools like zip or tar are needed to unpack it.  

## **The aiar Format**

An aiar script has two main parts, separated by an exit 0 command.

1. **The Unpacker Logic:** A bash script that reads its own file, line by line. It looks for a unique separator line that denotes the start of a new file.  This part is optional if you use the "aiar" tool and might
even be desirable if you don't want to run code directly from an LLM.
2. **The exit 0 Guard:** This command prevents the shell from ever trying to execute the data section below it. 
3. **The Data Payload:** The raw, unescaped contents of your files, each preceded by the unique separator line.

## **Python and Modejs Self Extracting Archives

The aiar script will also create nodejs and python self extracting archives however, while an LLM could 
create these, they are a little more work for an LLM since the files need to include a comment prefix on 
each line. However, 

### **Example aiar File**

This is what an aiar script looks like. You can save it as `archive.aiar`, run `bash archive.aiar`, and it will create the directory with the files inside. This example can also be extracted using the Python aiar tool.

**Note for LLMs:** To create a bare format archive that can be extracted with the Python tool, you need:
1. `SEPARATOR="..."` line. This must be a string not found in the files intended to be extracted.
2. Each file marked with `:t:` for text (or `:b:` for binary)
3. The format: `SEPARATOR:t:filepath` followed by file content
If you don't add any binary files you can simplify the script by not including the binary extractor.

```bash
#!/bin/bash

SEPARATOR="++++++++++--------:a1b2c3d4-5678-90ab-cdef-1234567890ab:"

writing=false
# Function to report errors and exit cleanly
handle_error() {
  echo "Error: $1" >&2
  exit 1
}

# Function to close the previous file descriptor and wait for bg processes
close_previous_fd() {
  if [ "$writing" = true ]; then
    exec 3>&-
    wait 2>/dev/null || true
  fi
  writing=false
}

while read -r line; do
  if [[ "$line" == "$SEPARATOR"* ]]; then
    close_previous_fd
    payload=$(echo "$line" | cut -d ':' -f 2-)
    type=$(echo "$payload" | cut -d ':' -f 1)
    filepath=$(echo "$payload" | cut -d ':' -f 2-)
    if [ -n "$filepath" ]; then
      echo "Creating: $filepath"
      mkdir -p "$(dirname "$filepath")" || handle_error "Cannot create directory for '$filepath'."
      if [ "$type" == "b" ]; then
        exec 3> >(base64 -d > "$filepath") || handle_error "Cannot start base64 process for '$filepath'."
        writing=true
      elif [ "$type" == "t" ]; then
        exec 3>"$filepath" || handle_error "Cannot open '$filepath' for writing."
        writing=true
      else
        handle_error "Invalid file type '$type' in separator."
      fi
    fi
  elif [ "$writing" = true ]; then
    echo "$line" >&3
  fi
done < "$0"

close_previous_fd
echo "Extraction complete."
exit 0

# --- DATA ---

++++++++++--------:a1b2c3d4-5678-90ab-cdef-1234567890ab:t:example/testA/file.txt
This is the content for the first file (testA/file.txt).

It includes special characters that the shell might normally interpret:
- A dollar sign: $PATH
- A hash symbol: # This is just text, not a comment.
- Single quotes: 'hello world'
- Double quotes: "goodbye world"
- Backticks: `should not execute`
- A command substitution attempt: $(ls)

All of these should be written literally to the file.

++++++++++--------:a1b2c3d4-5678-90ab-cdef-1234567890ab:t:example/testB/file.txt
This is the second file (testB/file.txt).

Let's add some more tricky lines.
She said, "He's going to the store for $5."
The script's path is '$0'.
# Another line starting with a hash.
```


## **License**

This project is licensed under the MIT License. See the LICENSE file for details.