# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
General Spyder completion API constants and enumerations.

The constants and enums presented on this file correspond to a superset of
those used by the Language Server Protocol (LSP), available at:
https://microsoft.github.io/language-server-protocol/specifications/specification-current/
"""

# Standard library imports
from typing import Any, Optional, Tuple, Union

# Third party imports
from qtpy.QtCore import Signal, QObject, Slot


# Supported LSP programming languages
SUPPORTED_LANGUAGES = [
    'Bash', 'C#', 'Cpp', 'CSS/LESS/SASS', 'Go', 'GraphQL', 'Groovy', 'Elixir',
    'Erlang', 'Fortran', 'Haxe', 'HTML', 'Java', 'JavaScript', 'JSON',
    'Julia', 'Kotlin', 'OCaml', 'PHP', 'R', 'Rust', 'Scala', 'Swift',
    'TypeScript'
]

# ------------------ WORKSPACE SYMBOLS CONSTANTS --------------------


class SymbolKind:
    """LSP workspace symbol constants."""
    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    CONSTRUCTOR = 9
    ENUM = 10
    INTERFACE = 11
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    STRING = 15
    NUMBER = 16
    BOOLEAN = 17
    ARRAY = 18
    OBJECT = 19
    KEY = 20
    NULL = 21
    ENUM_MEMBER = 22
    STRUCT = 23
    EVENT = 24
    OPERATOR = 25
    TYPE_PARAMETER = 26

    # Additional symbol constants (non-standard)
    BLOCK_COMMENT = 224
    CELL = 225


# Mapping between symbol enum and icons
SYMBOL_KIND_ICON = {
    SymbolKind.FILE: 'file',
    SymbolKind.MODULE: 'module',
    SymbolKind.NAMESPACE: 'namespace',
    SymbolKind.PACKAGE: 'package',
    SymbolKind.CLASS: 'class',
    SymbolKind.METHOD: 'method',
    SymbolKind.PROPERTY: 'property',
    SymbolKind.FIELD: 'field',
    SymbolKind.CONSTRUCTOR: 'constructor',
    SymbolKind.ENUM: 'enum',
    SymbolKind.INTERFACE: 'interface',
    SymbolKind.FUNCTION: 'function',
    SymbolKind.VARIABLE: 'variable',
    SymbolKind.CONSTANT: 'constant',
    SymbolKind.STRING: 'string',
    SymbolKind.NUMBER: 'number',
    SymbolKind.BOOLEAN: 'boolean',
    SymbolKind.ARRAY: 'array',
    SymbolKind.OBJECT: 'object',
    SymbolKind.KEY: 'key',
    SymbolKind.NULL: 'null',
    SymbolKind.ENUM_MEMBER: 'enum_member',
    SymbolKind.STRUCT: 'struct',
    SymbolKind.EVENT: 'event',
    SymbolKind.OPERATOR: 'operator',
    SymbolKind.TYPE_PARAMETER: 'type_parameter',
    SymbolKind.BLOCK_COMMENT: 'blockcomment',
    SymbolKind.CELL: 'cell'
}


# -------------------- WORKSPACE CONFIGURATION CONSTANTS ----------------------


class ResourceOperationKind:
    """LSP workspace resource operations."""
    # The client is able to create workspace files and folders
    CREATE = 'create'
    # The client is able to rename workspace files and folders
    RENAME = 'rename'
    # The client is able to delete workspace files and folders
    DELETE = 'delete'


class FileChangeType:
    CREATED = 1
    CHANGED = 2
    DELETED = 3


class FailureHandlingKind:
    """LSP workspace modification error codes."""
    # Applying the workspace change is simply aborted if one
    # of the changes provided fails. All operations executed before, stay.
    ABORT = 'abort'
    # All the operations succeed or no changes at all.
    TRANSACTIONAL = 'transactional'
    # The client tries to undo the applied operations, best effort strategy.
    UNDO = 'undo'
    # The textual changes are applied transactionally, whereas
    # creation/deletion/renaming operations are aborted.
    TEXT_ONLY_TRANSACTIONAL = 'textOnlyTransactional'


# -------------------- CLIENT CONFIGURATION SETTINGS --------------------------

# WorkspaceClientCapabilities define capabilities the
# editor / tool provides on the workspace

WORKSPACE_CAPABILITIES = {
    # The client supports applying batch edits to the workspace.
    # Request: An array of `TextDocumentEdit`s to express changes
    #          to n different text documents
    "applyEdit": True,

    # Workspace edition settings
    "workspaceEdit": {
        # The client supports versioned document changes.
        "documentChanges": True,
        # The resource operations that the client supports
        "resourceOperations": [ResourceOperationKind.CREATE,
                               ResourceOperationKind.RENAME,
                               ResourceOperationKind.DELETE],
        # Failure handling strategy applied by the client.
        "failureHandling": FailureHandlingKind.TRANSACTIONAL
    },

    # Did change configuration notification supports dynamic registration.
    "didChangeConfiguration": {
        # Reload server settings dynamically
        "dynamicRegistration": True
    },

    # The watched files notification is sent from the client to the server
    # when the client detects changes to files watched by
    # the language client.
    "didChangeWatchedFiles": {
        # Can be turned on/off dynamically
        "dynamicRegistration": True
    },

    # The workspace symbol request is sent from the client to the server to
    # list project-wide symbols matching the query string.
    "symbol": {
        # Can be turned on/off dynamically
        "dynamicRegistration": True
    },

    # The workspace/executeCommand request is sent from the client to the
    # server to trigger command execution on the server. In most cases the
    # server creates a WorkspaceEdit structure and applies the changes to
    # the workspace using the request workspace/applyEdit which is sent from
    # the server to the client.
    "executeCommand": {
        # Can be turned on/off dynamically
        "dynamicRegistration": True,
        # Specific capabilities for the `SymbolKind` in the `workspace/symbol`
        # request.
        "symbolKind": {
            # The symbol kind values the client supports.
            "valueSet": [value for value in SymbolKind.__dict__.values()
                         if isinstance(value, int)]
        }
    },
    # The client has support for workspace folders.
    "workspaceFolders": True,
    # The client supports `workspace/configuration` requests.
    "configuration": True
}

# TextDocumentClientCapabilities define capabilities the editor / tool
# provides on text documents.

TEXT_EDITOR_CAPABILITES = {
    # Editor supports file watching and synchronization (Required)
    "synchronization": {
        # File synchronization can be turned on/off.
        "dynamicRegistration": True,

        # The client (Spyder) will send a willSave notification
        # to the server when a file is about to be saved.
        "willSave": True,

        # The client (Spyder) supports sending a will save request and
        # waits for a response providing text edits which will
        # be applied to the document before it is saved.
        "willSaveWaitUntil": True,

        # The client (Spyder) supports did save notifications.
        # The document save notification is sent from the client to
        # the server when the document was saved in the client.
        "didSave": True
    },

    # Editor supports code completion operations.
    # The Completion request is sent from the client to the server to
    # compute completion items at a given cursor position.
    "completion": {
        # Code completion can be turned on/off dynamically.
        "dynamicRegistration": True,

        # Client (Spyder) supports snippets as insert text.
        # A snippet can define tab stops and placeholders with `$1`, `$2`
        # and `${3:foo}`. `$0` defines the final tab stop, it defaults to
        # the end of the snippet. Placeholders with equal identifiers are
        # linked, that is typing in one will update others too.
        "completionItem": {
            "snippetSupport": True
        }
    },

    # The hover request is sent from the client to the server to request
    # hover information at a given text document position.
    "hover": {
        # Hover introspection can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # The signature help request is sent from the client to the server to
    # request signature information at a given cursor position.
    "signatureHelp": {
        # Function/Class/Method signature hinting can be turned on/off
        # dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to find references.
    # The references request is sent from the client to the server to resolve
    # project-wide references for the symbol denoted by the given text
    # document position.
    "references": {
        # Find references can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to highlight different text sections at the same time.
    # The document highlight request is sent from the client to the server to
    # resolve a document highlights for a given text document position
    "documentHighlight": {
        # Code highlighting can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor supports finding symbols on a document.
    # The document symbol request is sent from the client to the server to list
    # all symbols found in a given text document.
    "documentSymbol": {
        # Find symbols on document can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to autoformat all the document.
    # The document formatting request is sent from the server to the client to
    # format a whole document.
    "formatting": {
        # Document formatting can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor can autoformat only a selected region on a document.
    # The document range formatting request is sent from the client to the
    # server to format a given range in a document.
    "rangeFormatting": {
        # Partial document formatting can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to format a document while an edit is taking place.
    # The document on type formatting request is sent from the client to the
    # server to format parts of the document during typing.
    "onTypeFormatting": {
        # On-Type formatting can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor has an option to go to a function/class/method definition.
    # The goto definition request is sent from the client to the server to
    # resolve the definition location of a symbol at a given text document
    # position.
    "definition": {
        # Go-to-definition can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor can give/highlight refactor tips/solutions.
    # The code action request is sent from the client to the server to compute
    # commands for a given text document and range. These commands are
    # typically code fixes to either fix problems or to beautify/refactor code.
    "codeAction": {
        # Code hints can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor can display additional commands/statistics per each line.
    # The code lens request is sent from the client to the server to compute
    # code lenses for a given text document.
    # A code lens represents a command that should be shown along with
    # source text, like the number of references, a way to run tests, etc.
    "codeLens": {
        # Code lens can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to find cross-document link references.
    # The document links request is sent from the client to the server to
    # request the location of links in a document.
    # A document link is a range in a text document that links to an internal
    # or external resource, like another text document or a web site.
    "documentLink": {
        # Finding document cross-references can be turned on/off dynamically.
        "dynamicRegistration": True
    },

    # Editor allows to rename a variable/function/reference globally
    # on a document.
    # The rename request is sent from the client to the server to perform
    # a workspace-wide rename of a symbol.
    "rename": {
        "dynamicRegistration": True
    }
}


# Spyder editor and workspace capabilities

CLIENT_CAPABILITES = {
    "workspace": WORKSPACE_CAPABILITIES,
    "textDocument": TEXT_EDITOR_CAPABILITES
}


# -------------------- SERVER CONFIGURATION SETTINGS --------------------------

# Text document synchronization mode constants

class TextDocumentSyncKind:
    """Text document synchronization modes supported by a lsp-server"""
    NONE = 0  # Text synchronization is not supported
    FULL = 1  # Text synchronization requires all document contents
    INCREMENTAL = 2  # Partial text synchronization is supported


# Save options.

SAVE_OPTIONS = {
    # The client is supposed to include the content on save.
    'includeText': True
}

# Text synchronization capabilities

TEXT_DOCUMENT_SYNC_OPTIONS = {
    # Open and close notifications are sent to the server.
    'openClose': True,

    # Change notifications are sent to the server.
    # See TextDocumentSyncKind.NONE, TextDocumentSyncKind.FULL
    # and TextDocumentSyncKind.INCREMENTAL.
    'change': TextDocumentSyncKind.NONE,

    # Will save notifications are sent to the server.
    'willSave': False,

    # Will save wait until requests are sent to the server.
    'willSaveWaitUntil': False,

    # Save notifications are sent to the server.
    'save': SAVE_OPTIONS
}


# Code completion options

COMPLETION_OPTIONS = {
    # The server provides support to resolve additional
    # information for a completion item.
    'resolveProvider': False,

    # The characters that trigger completion automatically.
    'triggerCharacters': []
}

# Signature help options

SIGNATURE_HELP_OPTIONS = {
    # The characters that trigger signature help automatically.
    'triggerCharacters': []
}

# Code lens options

CODE_LENS_OPTIONS = {
    # Code lens has a resolve provider as well.
    'resolveProvider': False
}

# Format document on type options

DOCUMENT_ON_TYPE_FORMATTING_OPTIONS = {
    # A character on which formatting should be triggered, like `}`.
    'firstTriggerCharacter': None,

    # More trigger characters.
    'moreTriggerCharacter': [],
}


# Document link options

DOCUMENT_LINK_OPTIONS = {
    # Document links have a resolve provider as well.
    'resolveProvider': False
}

# Execute command options.

EXECUTE_COMMAND_OPTIONS = {
    # The commands to be executed on the server
    'commands': []
}

# Workspace options.

WORKSPACE_OPTIONS = {
    # The server has support for workspace folders
    'workspaceFolders': {
        'supported': False,
        'changeNotifications': False
    }
}


# Server available capabilites options as defined by the protocol.

SERVER_CAPABILITES = {
    # Defines how text documents are synced.
    # Is either a detailed structure defining each notification or
    # for backwards compatibility the TextDocumentSyncKind number.
    'textDocumentSync': TEXT_DOCUMENT_SYNC_OPTIONS,

    # The server provides hover support.
    'hoverProvider': False,

    # The server provides completion support.
    'completionProvider': COMPLETION_OPTIONS,

    # The server provides signature help support.
    'signatureHelpProvider': SIGNATURE_HELP_OPTIONS,

    # The server provides goto definition support.
    'definitionProvider': False,

    # The server provides find references support.
    'referencesProvider': False,

    # The server provides document highlight support.
    'documentHighlightProvider': False,

    # The server provides document symbol support.
    'documentSymbolProvider': False,

    # The server provides workspace symbol support.
    'workspaceSymbolProvider': False,

    # The server provides code actions.
    'codeActionProvider': False,

    # The server provides code lens.
    'codeLensProvider': CODE_LENS_OPTIONS,

    # The server provides document formatting.
    'documentFormattingProvider': False,

    # The server provides document range formatting.
    'documentRangeFormattingProvider': False,

    # The server provides document formatting on typing.
    'documentOnTypeFormattingProvider': DOCUMENT_ON_TYPE_FORMATTING_OPTIONS,

    # The server provides rename support.
    'renameProvider': False,

    # The server provides document link support.
    'documentLinkProvider': DOCUMENT_LINK_OPTIONS,

    # The server provides execute command support.
    'executeCommandProvider': EXECUTE_COMMAND_OPTIONS,

    # Workspace specific server capabillities.
    'workspace': WORKSPACE_OPTIONS,

    # Experimental server capabilities.
    'experimental': None
}


class LSPEventTypes:
    """Language Server Protocol event types."""
    DOCUMENT = 'textDocument'
    WORKSPACE = 'workspace'
    WINDOW = 'window'
    CODE_LENS = 'codeLens'


class CompletionRequestTypes:
    """Language Server Protocol request/response types."""
    # General requests
    INITIALIZE = 'initialize'
    INITIALIZED = 'initialized'
    SHUTDOWN = 'shutdown'
    EXIT = 'exit'
    CANCEL_REQUEST = '$/cancelRequest'
    # Window requests
    WINDOW_SHOW_MESSAGE = 'window/showMessage'
    WINDOW_SHOW_MESSAGE_REQUEST = 'window/showMessageRequest'
    WINDOW_LOG_MESSAGE = 'window/logMessage'
    TELEMETRY_EVENT = 'telemetry/event'
    # Client capabilities requests
    CLIENT_REGISTER_CAPABILITY = 'client/registerCapability'
    CLIENT_UNREGISTER_CAPABILITY = 'client/unregisterCapability'
    # Workspace requests
    WORKSPACE_FOLDERS = 'workspace/workspaceFolders'
    WORKSPACE_FOLDERS_CHANGE = 'workspace/didChangeWorkspaceFolders'
    WORKSPACE_CONFIGURATION = 'workspace/configuration'
    WORKSPACE_CONFIGURATION_CHANGE = 'workspace/didChangeConfiguration'
    WORKSPACE_WATCHED_FILES_UPDATE = 'workspace/didChangeWatchedFiles'
    WORKSPACE_SYMBOL = 'workspace/symbol'
    WORKSPACE_EXECUTE_COMMAND = 'workspace/executeCommand'
    WORKSPACE_APPLY_EDIT = 'workspace/applyEdit'
    # Document requests
    DOCUMENT_PUBLISH_DIAGNOSTICS = 'textDocument/publishDiagnostics'
    DOCUMENT_DID_OPEN = 'textDocument/didOpen'
    DOCUMENT_DID_CHANGE = 'textDocument/didChange'
    DOCUMENT_WILL_SAVE = 'textDocument/willSave'
    DOCUMENT_WILL_SAVE_UNTIL = 'textDocument/willSaveWaitUntil'
    DOCUMENT_DID_SAVE = 'textDocument/didSave'
    DOCUMENT_DID_CLOSE = 'textDocument/didClose'
    DOCUMENT_COMPLETION = 'textDocument/completion'
    COMPLETION_RESOLVE = 'completionItem/resolve'
    DOCUMENT_HOVER = 'textDocument/hover'
    DOCUMENT_SIGNATURE = 'textDocument/signatureHelp'
    DOCUMENT_REFERENCES = ' textDocument/references'
    DOCUMENT_HIGHLIGHT = 'textDocument/documentHighlight'
    DOCUMENT_SYMBOL = 'textDocument/documentSymbol'
    DOCUMENT_FORMATTING = 'textDocument/formatting'
    DOCUMENT_FOLDING_RANGE = 'textDocument/foldingRange'
    DOCUMENT_RANGE_FORMATTING = 'textDocument/rangeFormatting'
    DOCUMENT_ON_TYPE_FORMATTING = 'textDocument/onTypeFormatting'
    DOCUMENT_DEFINITION = 'textDocument/definition'
    DOCUMENT_CODE_ACTION = 'textDocument/codeAction'
    DOCUMENT_CODE_LENS = 'textDocument/codeLens'
    CODE_LENS_RESOLVE = 'codeLens/resolve'
    DOCUMENT_LINKS = 'textDocument/documentLink'
    DOCUMENT_LINK_RESOLVE = 'documentLink/resolve'
    DOCUMENT_RENAME = 'textDocument/rename'
    # Spyder extensions to LSP
    DOCUMENT_CURSOR_EVENT = 'textDocument/cursorEvent'

# -------------------- LINTING RESPONSE RELATED VALUES ------------------------


class DiagnosticSeverity:
    """LSP diagnostic severity levels."""
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4

# ----------------- AUTO-COMPLETION RESPONSE RELATED VALUES -------------------


class CompletionItemKind:
    """LSP completion element categories."""
    TEXT = 1
    METHOD = 2
    FUNCTION = 3
    CONSTRUCTOR = 4
    FIELD = 5
    VARIABLE = 6
    CLASS = 7
    INTERFACE = 8
    MODULE = 9
    PROPERTY = 10
    UNIT = 11
    VALUE = 12
    ENUM = 13
    KEYWORD = 14
    SNIPPET = 15
    COLOR = 16
    FILE = 17
    REFERENCE = 18


class InsertTextFormat:
    """LSP completion text interpretations."""
    PLAIN_TEXT = 1
    SNIPPET = 2

# ----------------- SAVING REQUEST RELATED VALUES -------------------


class TextDocumentSaveReason:
    """LSP text document saving action causes."""
    MANUAL = 1
    AFTER_DELAY = 2
    FOCUS_OUT = 3

# ----------------------- INTERNAL CONSTANTS ------------------------


class ClientConstants:
    """Internal LSP Client constants."""
    CANCEL = 'lsp-cancel'

# ----------------------- WORKSPACE UPDATE CONSTANTS ----------------


class WorkspaceUpdateKind:
    ADDITION = 'addition'
    DELETION = 'deletion'


# ---------------- OTHER GENERAL PURPOSE CONSTANTS ------------------
COMPLETION_ENTRYPOINT = 'spyder.completions'

# -------------- SPYDER COMPLETION PROVIDER INTERFACE ---------------

class SpyderCompletionProvider(QObject):
    """
    Spyder plugin API for completion providers.

    All completion providers must implement this interface in order to interact
    with Spyder CodeEditor and Projects manager.
    """

    sig_response_ready = Signal(str, int, dict)
    """
    This signal is used to send a response back to the completion manager.

    Parameters
    ----------
    completion_client_name: str
        Name of the completion client that produced this response.
    request_seq: int
        Sequence number for the request.
    response: dict
        Actual request corpus response.
    """

    sig_provider_ready = Signal(str)
    """
    This signal is used to indicate that the completion provider is ready
    to handle requests.

    Parameters
    ----------
    completion_client_name: str
        Name of the completion client.
    """

    sig_language_client_available = Signal(dict, str)
    """
    This signal is used to indicate that completion capabilities are supported
    for a given programming language.

    Parameters
    ----------
    completion_capabilites: dict
        Available configurations supported by the client, it should conform to
        `spyder.plugins.completion.api.SERVER_CAPABILITES`.
    language: str
        Name of the programming language whose completion capabilites are
        available.
    """

    sig_disable_provider = Signal(str)
    """
    This signal is used to indicate that a completion provider should be
    disabled.

    Parameters
    ----------
    completion_provider_name: str
        Name of the completion provider to disable.
    """

    sig_show_widget = Signal(object)
    """
    This signal is used to display a graphical widget such as a QMessageBox.

    Parameters
    ----------
    widget: Union[QWidget, Callable[[QWidget], QWidget]]
        Widget to display, its constructor should receive parent as first and
        only argument.
    """

    sig_call_statusbar = Signal(str, str, tuple, dict)
    """
    This signal is used to call a remote method on a statusbar registered via
    the `STATUS_BAR` attribute.

    Parameters
    ----------
    statusbar_key: str
        Status bar key identifier that was registered on the `STATUS_BAR`
        attribute.
    method_name: str
        Name of the remote method defined on the statusbar.
    args: tuple
        Tuple with positional arguments to invoke the method.
    kwargs: dict
        Dictionary containing optional arguments to invoke the method.
    """

    sig_exception_occurred = Signal(dict)
    """
    This signal can be emitted to report an exception from any plugin.

    Parameters
    ----------
    error_data: dict
        The dictionary containing error data. The expected keys are:
        >>> error_data= {
            "text": str,
            "is_traceback": bool,
            "repo": str,
            "title": str,
            "label": str,
            "steps": str,
        }

    Notes
    -----
    The `is_traceback` key indicates if `text` contains plain text or a
    Python error traceback.

    The `title` and `repo` keys indicate how the error data should
    customize the report dialog and Github error submission.

    The `label` and `steps` keys allow customizing the content of the
    error dialog.

    This signal is automatically connected to the main Spyder interface.
    """

    # ---------------------------- ATTRIBUTES ---------------------------------

    # Name of the completion service
    # Status: Required
    COMPLETION_CLIENT_NAME = None

    # Define the priority of this provider, with 1 being the highest one
    # Status: Required
    DEFAULT_ORDER = -1

    # Define configuration defaults if using a separate file.
    # List of tuples, with the first item in the tuple being the section
    # name and the second item being the default options dictionary.
    #
    # CONF_DEFAULTS_EXAMPLE = [
    #     ('section-name', {'option-1': 'some-value',
    #                       'option-2': True,}),
    #     ('another-section-name', {'option-3': 'some-other-value',
    #                               'option-4': [1, 2, 3],}),
    # ]
    CONF_DEFAULTS = []

    # IMPORTANT NOTES:
    # 1. If you want to *change* the default value of a current option, you
    #    need to do a MINOR update in config version, e.g. from 3.0.0 to 3.1.0
    # 2. If you want to *remove* options that are no longer needed or if you
    #    want to *rename* options, then you need to do a MAJOR update in
    #    version, e.g. from 3.0.0 to 4.0.0
    # 3. You don't need to touch this value if you're just adding a new option
    CONF_VERSION = "0.1.0"

    # Widget to be used as entry in Spyder Preferences dialog.
    CONF_TABS = []

    # A map of status bars that the provider declares to display on Spyder.
    # Each status bar should correspond to a
    # :class:`spyder.api.widgets.status.StatusBarWidget` or
    # a closure that returns a StatusBarWidget.
    #
    # STATUS_BAR = {
    #     'statusbar_key1': StatusBarClass1,
    #     'statusbar_key2': StatusBarClass2,
    #     ...
    # }
    STATUS_BARS = {}

    def __init__(self, parent, config):
        """
        Main completion provider constructor.

        Parameters
        ----------
        parent: spyder.plugins.completion.plugin.CompletionPlugin
            Instance of the completion plugin that manages this provider
        config: dict
            Current provider configuration values, whose keys correspond to
            the ones defined on `CONF_DEFAULTS` and the values correspond to
            the current values according to the Spyder configuration.
        """
        QObject.__init__(self, parent)
        self.main = parent
        self.config = config

    def get_name(self) -> str:
        """Return a human readable name of the completion provider."""
        return ''

    def register_file(self, language: str, filename: str, codeeditor):
        """
        Register file to perform completions.
        If a language client is not available for a given file, then this
        method should keep a queue, such that files can be initialized once
        a server is available.

        Parameters
        ----------
        language: str
            Programming language of the given file
        filename: str
            Filename to register
        codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
            Codeeditor to send the client configurations
        """
        pass

    def send_request(
            self, language: str, req_type: str, req: dict, req_id: int):
        """
        Process completion/introspection request from Spyder.
        The completion request `req_type` needs to have a response.

        Parameters
        ----------
        language: str
            Programming language for the incoming request
        req_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.api.CompletionRequestTypes`
        req: dict
            Request body
            {
                'filename': str,
                **kwargs: request-specific parameters
            }
        req_id: int
            Request identifier for response
        """
        pass

    def send_notification(
            self, language: str, notification_type: str, notification: dict):
        """
        Send notification to completion server based on Spyder changes.

        Parameters
        ----------
        language: str
            Programming language for the incoming request
        notification_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.api.CompletionRequestTypes`
        notification: dict
            Request body
            {
                'filename': str,
                **kwargs: request-specific parameters
            }
        """
        pass

    def broadcast_notification(
            self, notification_type: str, notification: dict):
        """
        Send a broadcast notification across all programming languages.

        Parameters
        ----------
        req_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.CompletionTypes`
        req: dict
            Request body
            {
                **kwargs: notification-specific parameters
            }
        req_id: int
            Request identifier for response, None if notification
        """
        pass

    def send_response(self, response: dict, resp_id: int):
        """
        Send response for server request.

        Parameters
        ----------
        response: dict
            Response body for server
            {
                **kwargs: response-specific keys
            }
        resp_id: int
            Request identifier for response
        """
        pass

    def update_configuration(self, config: dict):
        """
        Handle completion option configuration updates.

        Parameters
        ----------
        conf: dict
            Dictionary containing the new provider configuration
        """
        pass

    def project_path_update(self, project_path: str, update_kind: str,
                            instance: Any):
        """
        Handle project path updates on Spyder.

        Parameters
        ----------
        project_path: str
            Path to the project folder modified
        update_kind: str
            Path update kind, one of
            :class:`spyder.plugins.completion.api.WorkspaceUpdateKind`
        instance: object
            Reference to :class:`spyder.plugins.projects.plugin.Projects`
        """
        pass

    @Slot(object, object)
    def python_path_update(self, previous_path, new_path):
        """
        Handle Python path updates on Spyder.

        Parameters
        ----------
        previous_path: Dict
            Dictionary containing the previous Python path values
        new_path: Dict
            Dictionary containing the current Python path values.
        """
        pass

    @Slot()
    def main_interpreter_changed(self):
        """Handle changes on the main Python interpreter of Spyder."""
        pass

    def file_opened_updated(self, filename: str, language: str):
        """
        Handle file modifications and file switching events, including when a
        new file is created.

        Parameters
        ----------
        filename: str
            Path to the file that was changed/opened/focused.
        language: str
            Name of the programming language of the file that was
            changed/opened/focused.
        """
        pass

    def start_provider(self, language: str) -> bool:
        """
        Start completions/introspection services for a given language.

        Parameters
        ----------
        language: str
            Programming language to start analyzing

        Returns
        -------
        bool
            True if language client could be started, otherwise False.
        """
        return False

    def stop_provider(self, language: str):
        """
        Stop completions/introspection services for a given language.

        Parameters
        ----------
        language: str
            Programming language to stop analyzing
        """
        pass

    def start(self):
        """Start completion plugin."""
        self.sig_provider_ready.emit(self.COMPLETION_CLIENT_NAME)

    def shutdown(self):
        """Stop completion plugin."""
        pass

    def can_close(self) -> bool:
        """Establish if the current completion provider can be stopped."""
        return True

    def get_option(self,
                   option_name: Union[str, Tuple[str, ...]],
                   default: Any = None,
                   section: Optional[str] = None) -> Any:
        """
        Retrieve an option value from the provider settings dictionary or
        from the global Spyder configurations.

        Parameters
        ----------
        option_name: str
            Option name to lookup for in the provider settings
            dictionary/global Spyder configurations.
        default: Any
            Default value to return if `option_name` was not found.
        section: Optional[str]
            If None, then the option is retrieved from the local provider
            configurations. Otherwise, lookup on the global Spyder
            configurations.

        Returns
        -------
        Any
            Either the default value if `option_name` was not found on the
            settings or the actual value stored.
        """
        if section is None:
            section = 'completions'
            if isinstance(option_name, tuple):
                option_name = (
                    'provider_configuration',
                    self.COMPLETION_CLIENT_NAME,
                    'values',
                    *option_name
                )
            else:
                option_name = (
                    'provider_configuration',
                    self.COMPLETION_CLIENT_NAME,
                    'values',
                    option_name
                )
        return self.main.get_global_option(
            option_name, section, default)

    def set_option(self,
                   option_name: Union[str, Tuple[str, ...]],
                   value: Any,
                   section: Optional[str] = None):
        """
        Set an option in the provider configuration settings dictionary or
        in the global Spyder configurations.

        Parameters
        ----------
        option_name: str
            Option name to lookup for in the provider settings
            dictionary/global Spyder configurations.
        value: Any
            Value to set in the configuration entry.
        section: Optional[str]
            If None, then the option is retrieved from the local provider
            configurations. Otherwise, lookup on the global Spyder
            configurations.
        """
        if section is None:
            section = 'completions'
            if isinstance(option_name, tuple):
                option_name = (
                    'provider_configuration',
                    self.COMPLETION_CLIENT_NAME,
                    'values',
                    *option_name
                )
            else:
                option_name = (
                    'provider_configuration',
                    self.COMPLETION_CLIENT_NAME,
                    'values',
                    option_name
                )
        self.main.set_conf_option(option_name, value, section)

    def on_mainwindow_visible(self):
        """
        Actions to be performed after the main window's has been shown.
        """
        pass
