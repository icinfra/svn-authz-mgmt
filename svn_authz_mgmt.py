#!/bin/env python3

import json
import curses
import re
import subprocess
import argparse

def user_exists(username):
    """Check if a user exists in the system by calling 'id <username>'."""
    try:
        subprocess.run(['id', username], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def edit_permissions(stdscr, path, permissions):
    curses.echo()
    curses.curs_set(1)  # Show cursor for editing
    stdscr.keypad(True)  # Enable special keys processing

    # Display prompt
    prompt = f"Edit permissions for {path} (format: user=perm,user=perm): "
    stdscr.addstr(0, 0, prompt)

    # Load current permissions for editing
    current_perms = ", ".join(f"{user}={perm}" for user, perm in permissions.get(path, {}).items())
    stdscr.addstr(0, len(prompt), current_perms)

    # Manage input editing
    input_str = list(current_perms)
    col = len(current_perms)

    while True:
        stdscr.move(0, len(prompt) + col)  # Move cursor to correct position
        key = stdscr.getch()

        if key == curses.KEY_LEFT and col > 0:
            col -= 1
        elif key == curses.KEY_RIGHT and col < len(input_str):
            col += 1
        elif key == curses.KEY_BACKSPACE or key == 127:
            if col > 0:
                del input_str[col - 1]
                col -= 1
        elif key == 10 or key == curses.KEY_ENTER:  # Enter key
            break
        elif 32 <= key <= 126:  # Printable characters
            input_str.insert(col, chr(key))
            col += 1

        # Re-display input field with changes
        stdscr.move(0, len(prompt))
        stdscr.clrtoeol()  # Clear old input
        stdscr.addstr(0, len(prompt), ''.join(input_str))

    new_perms = ''.join(input_str).strip()
    curses.noecho()
    curses.curs_set(0)  # Hide cursor after editing

    # Update permissions dictionary based on new input
    if new_perms == "":
        if path in permissions:
            del permissions[path]
    else:
        new_dict = {}
        for perm in re.split(r' *, *', new_perms):
            if '=' in perm:
                user, perm = re.split(r'[ =]+', perm)
                if perm in ["", "r", "rw"]:
                    if user.strip() == "*" or user_exists(user.strip()):
                        new_dict[user.strip()] = perm.strip()
        permissions[path] = new_dict

    return permissions

def save_permissions_to_file(permissions, authz_file, repo_id):
    # Load existing permissions from file to preserve other repo_id entries
    existing_permissions = load_permissions(authz_file)
    
    # Update only the sections belonging to the specified repo_id
    for section in list(existing_permissions.keys()):
        if section.startswith(f"{repo_id}:"):
            del existing_permissions[section]  # Remove old section
    for section, perms in permissions.items():
        existing_permissions[f"{repo_id}:{section}"] = perms  # Add updated/new section

    # Write all permissions back to the file
    with open(authz_file, 'w') as file:
        for section, perms in sorted(existing_permissions.items()):
            file.write(f"[{section}]\n")
            for user, perm in perms.items():
                file.write(f"{user} = {perm}\n")

def load_permissions(authz_file):
    permissions = {}
    all_permissions = {}
    try:
        with open(authz_file, 'r') as file:
            current_section = None
            for line in file:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    all_permissions[current_section] = {}
                elif '=' in line and current_section:
                    user, perm = line.split('=')
                    all_permissions[current_section][user.strip()] = perm.strip()
    except FileNotFoundError:
        print(f"Error: File {authz_file} not found.")
    return all_permissions

def svn_list(url, depth, permissions, prefix='', current_depth=0, tree=None):
    if tree is None:
        tree = {}
        if current_depth == 0:
            tree["/"] = {"__perm__": permissions.get("/", {}), "__depth__": 0}
    if current_depth >= depth:
        return tree
    try:
        result = subprocess.run(['svn', 'ls', url], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)
        lines = result.stdout.splitlines()
        for line in lines:
            name = line.strip('/')
            new_url = url.rstrip('/') + '/' + name
            current_prefix = prefix + name + '/'
            if line.endswith('/'):
                sub_tree = svn_list(new_url, depth, permissions, current_prefix, current_depth + 1)
                tree[name + '/'] = sub_tree
            else:
                tree[name] = {}

            if current_prefix.strip("/") in permissions:
                tree[line]['__perm__'] = permissions[current_prefix.strip("/")]
                tree[line]['__depth__'] = current_depth + 1
    except subprocess.CalledProcessError as e:
        print(f"Error executing svn ls on {url}: {e}")
    return tree


def get_display_items(tree, prefix='', expanded=set(), level=0):
    items = []
    display_map = {}
    index = 0

    for key, value in tree.items():
        # Skip the special keys
        if key.startswith('__') and key.endswith('__'):
            continue

        base_item = prefix + key

        # Determine the indent based on the level
        # Add 4 extra spaces for all levels except the root
        if key == "/":
            indent = ''
        else:
            indent = ' ' * 4 * (level + 1)

        display_item = indent + key
        perm_display = ""

        # Prepare the permissions display string
        if '__perm__' in value:
            perm_info = ", ".join([f"{user}={perm}" for user, perm in value['__perm__'].items()])
            perm_display = f" [Permissions: {perm_info}]"

        # Add the expand/collapse indicator if it's a directory
        if isinstance(value, dict):
            expanded_key = base_item + '/' if not base_item.endswith('/') else base_item
            if expanded_key in expanded and value:  # Only if directory has contents
                display_item += " [-]" + perm_display
                items.append(display_item)
                display_map[index] = base_item
                index += 1
                # Recursively add the sub-items
                sub_items, sub_map = get_display_items(value, expanded_key, expanded, level + 1)
                items.extend(sub_items)
                display_map.update({k + index: v for k, v in sub_map.items()})
                index += len(sub_items)
            else:
                if value:
                    display_item += " [+]" + perm_display
                else:
                    display_item += perm_display
                items.append(display_item)
                display_map[index] = base_item
                index += 1
        else:
            # If it's a file or empty directory, just add the permissions display
            display_item += perm_display
            items.append(display_item)
            display_map[index] = base_item
            index += 1

    return items, display_map



def expand_or_collapse_all(tree, path, expanded, is_expand):
    for key, val in tree.items():
        if isinstance(val, dict):
            full_path = (path + key).rstrip('/') + '/'
            if is_expand:
                expanded.add(full_path)
                expand_or_collapse_all(val, full_path, expanded, is_expand)
            else:
                expand_or_collapse_all(val, full_path, expanded, is_expand)
                if full_path in expanded:
                    expanded.remove(full_path)

def main(stdscr, authz_file, repository_url, repo_id, depth=4):
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    expanded = set()
    current_row = 0
    top_row = 0

    all_permissions = load_permissions(authz_file)
    permissions = {k.split(':', 1)[1]: v for k, v in all_permissions.items() if k.startswith(f"{repo_id}:")}
    tree_structure = svn_list(repository_url, depth, permissions)

    while True:
        items, display_map = get_display_items(tree_structure, expanded=expanded)
        stdscr.clear()
        height, width = stdscr.getmaxyx()  # Get the dimensions of the screen
        max_row = height - 1

        for idx in range(top_row, min(top_row + height, len(items))):
            row = items[idx]
            display_idx = idx - top_row  # Adjust index to start from 0
            if idx == current_row:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(display_idx, 0, row)
                stdscr.attroff(curses.color_pair(1))
            else:
                stdscr.addstr(display_idx, 0, row)
        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
            if current_row < top_row:
                top_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(items) - 1:
            current_row += 1
            if current_row >= top_row + height:
                top_row += 1
        elif key == ord('q'):
            break
        elif key in [ord('\n'), curses.KEY_ENTER]:
            full_path = display_map[current_row]
            if full_path in expanded:
                expanded.remove(full_path)
                to_remove = [item for item in expanded if item.startswith(full_path + '/')]
                for item in to_remove:
                    expanded.remove(item)
            else:
                expanded.add(full_path)
        elif key == ord('x'):  # Expand all
            expand_or_collapse_all(tree_structure, '', expanded, True)
        elif key == ord('c'):  # Collapse all
            expand_or_collapse_all(tree_structure, '', expanded, False)
        elif key == ord('e'):
            path = display_map[current_row]
            if path == "/":
                path = "/"
            elif path.endswith('/'):
                path = path[:-1]  # Remove trailing slash for directory
            permissions = edit_permissions(stdscr, path, permissions)
        elif key == ord('s'):
            save_permissions_to_file(permissions, authz_file, repo_id)
            stdscr.addstr(0, 0, "Permissions saved successfully.")
            stdscr.refresh()
            stdscr.getch()  # Wait for user to press a key


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage SVN repository permissions.")
    parser.add_argument('repository_url', type=str, help='The URL of the SVN repository')
    parser.add_argument('repo_id', type=str, help='The repository identifier')
    parser.add_argument('authz_file', type=str, help='Path to the authz file')
    parser.add_argument('--depth', type=int, default=4, help='Depth of directory structure to display (default: 4)')
    
    args = parser.parse_args()
    
    curses.wrapper(main, args.authz_file, args.repository_url, args.repo_id, args.depth)
