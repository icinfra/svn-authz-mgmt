# Subversion Authz Management Tool

This tool provides a comprehensive interface for managing Subversion (SVN) repository permissions. Built with Python and utilizing the `curses` library, it allows for interactive browsing and modification of permissions directly from the command line.

## Features

- **Interactive Tree Navigation**: Browse the structure of your SVN repository in a tree-like interface.
- **Edit Permissions**: Modify user permissions for any file or directory within the repository.
- **Validation of User Accounts**: Ensures that permissions are only assigned to existing system users.
- **Save Changes**: Persist your changes directly to the SVN authorization (authz) file.
- **Expand and Collapse Views**: Easily manage visual complexity by expanding or collapsing directories.

## Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/<your-username>/subversion-authz-management.git
   ```
2. **Navigate to the Project Directory:**
   ```bash
   cd subversion-authz-management
   ```

## Dependencies

Ensure you have Python 3 installed on your system. This program relies on external commands like `svn` and `id`, so make sure these are available on your system.

## Usage

To run the tool, you can use the following command:

```bash
./svn_authz_mgmt.py <repository_url> <repo_id> <authz_file> --depth <depth>
```

### Command Line Arguments:

- `repository_url`: URL to your SVN repository.
- `repo_id`: Identifier for the repository, used to manage permissions specific to the repository.
- `authz_file`: Path to the SVN authorization file.
- `depth`: (Optional) Depth of directory structure to display (default is 4).

### Interactive Commands:

- **Navigation**: Use arrow keys to move up and down through the repository tree.
- **Expand/Collapse**: Press 'x' to expand all and 'c' to collapse all.
- **Edit**: Press 'e' to edit permissions for the selected directory or file.
- **Save**: Press 's' to save changes to the authorization file.
- **Quit**: Press 'q' to exit the tool.

## Contributing

Contributions to the Subversion Authz Management Tool are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
