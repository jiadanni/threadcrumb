"""Centralized CSS selectors for Slack's DOM.

All selectors live here so there's a single file to update when Slack changes its UI.
Verified against live Slack DOM March 2026.
"""

# --- Authentication / logged-in detection ---
# These are broad checks; is_logged_in() also checks URL patterns
CLIENT_CONTAINER = ".p-client_container"
MESSAGE_INPUT = '[data-qa="message_input"]'
CHANNEL_SIDEBAR = '[data-qa="channel-sidebar"]'
TOP_NAV = '[data-qa="top-nav"]'
TAB_RAIL = '[data-qa="tab_rail_desktop"]'

# --- Channel sidebar ---
CHANNEL_SIDEBAR_CHANNEL = '[data-qa="channel-sidebar-channel"]'
CHANNEL_SIDEBAR_DM = '[data-qa="channel-sidebar-dm"]'
CHANNEL_SIDEBAR_NAME = ".p-channel_sidebar__name"
CHANNEL_SIDEBAR_LINK = ".p-channel_sidebar__link"
CHANNEL_SIDEBAR_SECTION_HEADER = '[data-qa="channel-sidebar-section-header-button"]'
CHANNEL_SIDEBAR_SECTION_LABEL = ".p-channel_sidebar__section_heading_label"

# --- Message list ---
MESSAGE_LIST_CONTAINER = ".c-virtual_list__scroll_container"
MESSAGE_ITEM = '[data-qa="virtual-list-item"]'
MESSAGE_SENDER = '[data-qa="message_sender_name"]'
MESSAGE_TEXT = '[data-qa="message-text"]'
MESSAGE_BODY = ".c-message_kit__blocks"
MESSAGE_CONTENT = '[data-qa="message_content"]'
MESSAGE_CONTAINER = '[data-qa="message_container"]'

# --- Timestamps ---
# Slack uses a.c-timestamp with aria-label like "Today at 14:02:38"
MESSAGE_TIMESTAMP = "a.c-timestamp"
MESSAGE_TIMESTAMP_LABEL = ".c-timestamp__label"

# --- Reactions ---
REACTION_BAR = '[data-qa="reaction_bar"]'
REACTION_ITEM = '[data-qa="reactji"]'
# Reaction buttons have aria-label like "1 reaction, react with thumbsup emoji"
ADD_REACTION_BUTTON = '[data-qa="add_reaction_button"]'

# --- Thread indicators ---
# Reply bars use data-qa="reply-bar" but may have changed;
# look for reply count in message actions
REPLY_BAR = '[data-qa="reply-bar"]'
REPLY_COUNT_BUTTON = '[data-qa="reply_bar_count"]'
# Fallback: look for reply indicators by class
REPLY_BAR_FALLBACK = ".c-message_kit__reply_bar"

# --- Thread panel ---
THREAD_PANEL = '[data-qa="threads_flexpane"]'
THREAD_PANEL_FALLBACK = ".p-flexpane__preview-mode-overlay"
THREAD_PANEL_MESSAGES = f'{THREAD_PANEL} {MESSAGE_ITEM}'
THREAD_PANEL_CLOSE = 'button[aria-label="Close"]'

# --- Scroll / loading ---
MESSAGE_PANE = '[data-qa="message_pane"]'
SCROLL_CONTAINER = ".c-virtual_list__scroll_container"
DAY_DIVIDER = '[data-qa="day-divider-label"]'
CHANNEL_BEGINNING_MARKER = '[data-qa="channel_created_message"]'
LOADING_SPINNER = '[data-qa="loading_indicator"]'

# --- Search ---
SEARCH_BUTTON = '[data-qa="top_nav_search"]'
SEARCH_INPUT = 'button[aria-label="Search"]'
SEARCH_INPUT_FIELD = '[data-qa="search_input"]'
SEARCH_RESULTS_LIST = '[data-qa="search_message_results"]'
SEARCH_RESULT_ITEM = '[data-qa="search_message_result"]'
SEARCH_TAB_MESSAGES = '[data-qa="search_tab_messages"]'

# --- Bot messages ---
BOT_LABEL = '[data-qa="bot_label"]'
APP_BADGE = ".c-app_badge"

# --- Attachments ---
ATTACHMENT_IMAGE = '[data-qa="attachment_image"]'
FILE_ATTACHMENT = '[data-qa="message_file"]'

# --- Navigation ---
CHANNEL_NAME_BUTTON = '[data-qa="channel_name_button"]'
CHANNEL_NAME = '[data-qa="channel_name"]'
VIEW_HEADER = '[data-qa="view_header"]'

# --- Composer ---
TEXTY_INPUT = '[data-qa="texty_input"]'

# --- Custom status ---
CUSTOM_STATUS = '[data-qa="custom_status"]'
EMOJI = '[data-qa="emoji"]'
