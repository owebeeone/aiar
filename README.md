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

1. **The Unpacker Logic:** A bash script that reads its own file, line by line. It looks for a unique separator line that denotes the start of a new file.  
2. **The exit 0 Guard:** This command prevents the shell from ever trying to execute the data section below it.  
3. **The Data Payload:** The raw, unescaped contents of your files, each preceded by the unique separator line.

### **Example aiar File**

This is what an aiar script looks like. You can save it as archive.aiar, run bash archive.aiar, and it will create the aiar/ directory with the files inside.

```bash
#!/bin/bash

writing=false
handle_error() {
  echo "Error: $1" >&2
  exit 1
}

while read -r line; do
  if [[ "$line" == "++++++++++--------:"* ]]; then
    if [ "$writing" = true ]; then
      exec 3>&-
      writing=false
    fi
    filepath=$(echo "$line" | cut -d ':' -f 2-)
    if [ -n "$filepath" ]; then
      mkdir -p "$(dirname "$filepath")" || handle_error "Cannot create directory for '$filepath'. Check permissions."
      echo "Creating: $filepath"
      exec 3>"$filepath" || handle_error "Cannot open '$filepath' for writing. Check permissions."
      writing=true
    fi
  elif [ "$writing" = true ]; then
    echo "$line" >&3
  fi
done < "$0"

if [ "$writing" = true ]; then
  exec 3>&-
fi
exit 0

# --- DATA ---

++++++++++--------:llm_shar/testA/file.txt
This is the content for the first file (testA/file.txt).

It includes special characters that the shell might normally interpret:
- A dollar sign: $PATH
- A hash symbol: # This is just text, not a comment.
- Single quotes: 'hello world'
- Double quotes: "goodbye world"
- Backticks: `should not execute`
- A command substitution attempt: $(ls)

All of these should be written literally to the file.

++++++++++--------:llm_shar/testB/file.txt
This is the second file (testB/file.txt).

Let's add some more tricky lines.
She said, "He's going to the store for $5."
The script's path is '$0'.
# Another line starting with a hash.
```


## **License**

This project is licensed under the MIT License. See the LICENSE file for details.