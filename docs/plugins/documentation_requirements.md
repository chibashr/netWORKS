# Plugin Documentation Requirements

Each plugin must include proper documentation to ensure both users and other plugin developers understand its functionality and how to interact with it. This document outlines the documentation standards for netWORKS plugins.

## Required Documentation Files

Every plugin must include the following documentation:

1. **User Documentation (`README.md`)**: Provides information for end users on how to use the plugin
2. **API Documentation (`API.md`)**: Required if your plugin exposes functionality to other plugins

## User Documentation (README.md)

Every plugin must include a `README.md` file in its root directory. This file should include:

### Required Sections

1. **Plugin Name and Description**: Brief overview of what the plugin does
2. **Features**: List of main features and capabilities
3. **Installation**: Any special installation instructions (beyond placing in the plugins directory)
4. **Usage**: How to use the plugin, including UI locations and functionality
5. **Configuration**: Available configuration options, if any
6. **Dependencies**: External dependencies required by the plugin

### Optional Sections

1. **Screenshots**: Visual examples of the plugin in action
2. **Troubleshooting**: Common issues and their solutions
3. **License**: Plugin license information
4. **Version History**: Changes in each version
5. **Credits/Acknowledgements**: Credits to contributors or third-party resources

## Developer Documentation (API.md)

For plugins that expose functionality to other plugins, API documentation is required. This documentation must be provided in an `API.md` file in your plugin's root directory following the template found in `docs/plugins/API.md`.

The API.md documentation should include:

### Required Sections

1. **API Version**: The version of your plugin's API and compatibility information
2. **Overview**: Brief description of the API's purpose and functionality
3. **Exported Functions**: All functions that other plugins can call
   - Function name and parameters
   - Description of what the function does
   - Parameter descriptions (type and purpose)
   - Return value description
   - Example usage code
4. **Events/Hooks**: Events that the plugin emits or hooks it provides
   - Event name
   - Description of when the event is triggered
   - Data structure passed with the event
   - Example of how to register for the event
5. **Data Structures**: Format and documentation of data objects used by the API

### Optional Sections

1. **Integration Examples**: Complete examples showing how to use the API
2. **Version History**: Changes between API versions and any breaking changes
3. **Best Practices**: Recommendations for using the API effectively

## Documentation Format and Style

To maintain consistency across all plugin documentation:

1. **Use Markdown**: Format all documentation using proper Markdown syntax
2. **Include Code Examples**: Provide code snippets for all API functions and events
3. **Be Clear and Concise**: Use clear language and avoid unnecessary jargon
4. **Use Headers**: Organize content with appropriate heading levels
5. **Include Type Information**: Specify types for all parameters and return values

## Documentation Verification

The plugin manager will check for both README.md and API.md (if your plugin exports functionality) when loading plugins. Missing or incomplete documentation will generate warnings in the log and be visible in the Plugin Manager UI.

## Example Documentation

For a complete example of properly documented plugin, refer to the example plugin in `docs/plugins/example_plugin/`. This example includes both a comprehensive README.md and a well-structured API.md that follow these guidelines.

## Documentation Best Practices

1. **Keep Documentation Updated**: Documentation should be updated whenever functionality changes
2. **Include Version Information**: Add version numbers for API changes
3. **Document Breaking Changes**: Clearly mark any breaking changes between versions
4. **Use Consistent Terminology**: Use the same terms throughout your documentation
5. **Consider International Users**: Write in clear, simple language for non-native English speakers 