"""Tool definitions and handlers for ServiceNow operations."""

from collections.abc import Awaitable
from typing import Any, Callable, Optional

from mcp.types import Tool

from .client import ServiceNowClient
from .config import FeaturesConfig


class ToolRegistry:
    """Registry for ServiceNow MCP tools."""

    def __init__(self, features: FeaturesConfig):
        """Initialize tool registry with feature configuration."""
        self.features = features
        self._tools: dict[str, Tool] = {}
        self._handlers: dict[str, Callable[..., Awaitable[Any]]] = {}

        # Register all tools
        self._register_all_tools()

    def get_enabled_tools(self) -> list[Tool]:
        """Get list of enabled tools based on feature configuration."""
        enabled_tools = []

        for name, tool in self._tools.items():
            # Check if tool's feature is enabled
            if self._is_tool_enabled(name):
                enabled_tools.append(tool)

        return enabled_tools

    def get_handler(self, name: str) -> Optional[Callable[..., Awaitable[Any]]]:
        """Get handler for a specific tool."""
        return self._handlers.get(name)

    def _is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled based on features."""
        feature_map = {
            "incident": self.features.incident_management,
            "change": self.features.change_management,
            "problem": self.features.problem_management,
            "catalog": self.features.service_catalog,
            "ritm": self.features.service_catalog,
            "kb": self.features.knowledge_base,
            "user": self.features.user_management,
            "cmdb": self.features.cmdb,
            "ci": self.features.cmdb,
        }

        for prefix, enabled in feature_map.items():
            if tool_name.startswith(prefix) and not enabled:
                return False

        # Custom table tools are controlled by custom_tables feature
        if tool_name.startswith(
            (
                "query_table",
                "get_record",
                "create_record",
                "update_record",
                "delete_record",
            )
        ):
            return self.features.custom_tables

        return True

    def _register_all_tools(self) -> None:
        """Register all available tools."""

        # Table operations (custom tables)
        self._register_tool(
            "query_table",
            Tool(
                name="query_table",
                description="Query records from any ServiceNow table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "description": "Table name (e.g., incident, change_request)",
                        },
                        "query": {
                            "type": "string",
                            "description": "Encoded query string (e.g., 'active=true^priority=1')",
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of fields to return",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of records",
                            "default": 100,
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of records to skip",
                            "default": 0,
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Field to order by (prefix with - for descending)",
                        },
                    },
                    "required": ["table"],
                },
            ),
            self._handle_query_table,
        )

        self._register_tool(
            "get_record",
            Tool(
                name="get_record",
                description="Get a single record by sys_id",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                        "sys_id": {
                            "type": "string",
                            "description": "System ID of the record",
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of fields to return",
                        },
                    },
                    "required": ["table", "sys_id"],
                },
            ),
            self._handle_get_record,
        )

        self._register_tool(
            "create_record",
            Tool(
                name="create_record",
                description="Create a new record in a table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                        "data": {
                            "type": "object",
                            "description": "Record data as key-value pairs",
                        },
                    },
                    "required": ["table", "data"],
                },
            ),
            self._handle_create_record,
        )

        self._register_tool(
            "update_record",
            Tool(
                name="update_record",
                description="Update an existing record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                        "sys_id": {
                            "type": "string",
                            "description": "System ID of the record",
                        },
                        "data": {
                            "type": "object",
                            "description": "Fields to update as key-value pairs",
                        },
                    },
                    "required": ["table", "sys_id", "data"],
                },
            ),
            self._handle_update_record,
        )

        self._register_tool(
            "delete_record",
            Tool(
                name="delete_record",
                description="Delete a record from a table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                        "sys_id": {
                            "type": "string",
                            "description": "System ID of the record",
                        },
                    },
                    "required": ["table", "sys_id"],
                },
            ),
            self._handle_delete_record,
        )

        # Incident Management
        self._register_tool(
            "incident_create",
            Tool(
                name="incident_create",
                description="Create a new incident",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "short_description": {
                            "type": "string",
                            "description": "Brief description of the incident",
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description",
                        },
                        "urgency": {
                            "type": "integer",
                            "description": "Urgency (1=High, 2=Medium, 3=Low)",
                            "enum": [1, 2, 3],
                        },
                        "impact": {
                            "type": "integer",
                            "description": "Impact (1=High, 2=Medium, 3=Low)",
                            "enum": [1, 2, 3],
                        },
                        "assignment_group": {
                            "type": "string",
                            "description": "Assignment group name or sys_id",
                        },
                        "assigned_to": {
                            "type": "string",
                            "description": "User email or sys_id",
                        },
                        "category": {
                            "type": "string",
                            "description": "Incident category",
                        },
                        "subcategory": {
                            "type": "string",
                            "description": "Incident subcategory",
                        },
                    },
                    "required": ["short_description"],
                },
            ),
            self._handle_incident_create,
        )

        self._register_tool(
            "incident_update",
            Tool(
                name="incident_update",
                description="Update an existing incident",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": "string",
                            "description": "Incident number (e.g., INC0000001)",
                        },
                        "state": {
                            "type": "integer",
                            "description": "State (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed)",
                            "enum": [1, 2, 3, 6, 7],
                        },
                        "work_notes": {
                            "type": "string",
                            "description": "Work notes (internal)",
                        },
                        "comments": {
                            "type": "string",
                            "description": "Customer visible comments",
                        },
                        "resolution_code": {
                            "type": "string",
                            "description": "Resolution code when resolving",
                        },
                        "resolution_notes": {
                            "type": "string",
                            "description": "Resolution notes",
                        },
                    },
                    "required": ["number"],
                },
            ),
            self._handle_incident_update,
        )

        self._register_tool(
            "incident_search",
            Tool(
                name="incident_search",
                description="Search for incidents",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "assigned_to": {
                            "type": "string",
                            "description": "Filter by assigned user",
                        },
                        "assignment_group": {
                            "type": "string",
                            "description": "Filter by assignment group",
                        },
                        "state": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Filter by states",
                        },
                        "priority": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Filter by priorities",
                        },
                        "created_after": {
                            "type": "string",
                            "description": "Created after date (YYYY-MM-DD)",
                        },
                        "text_search": {
                            "type": "string",
                            "description": "Search in short description and description",
                        },
                        "limit": {"type": "integer", "default": 50},
                    },
                },
            ),
            self._handle_incident_search,
        )

        # Change Management
        self._register_tool(
            "change_create",
            Tool(
                name="change_create",
                description="Create a new change request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "short_description": {
                            "type": "string",
                            "description": "Brief description of the change",
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description",
                        },
                        "type": {
                            "type": "string",
                            "description": "Change type (normal, standard, emergency)",
                            "enum": ["normal", "standard", "emergency"],
                        },
                        "risk": {
                            "type": "integer",
                            "description": "Risk level (1=High, 2=Medium, 3=Low, 4=None)",
                            "enum": [1, 2, 3, 4],
                        },
                        "impact": {
                            "type": "integer",
                            "description": "Impact (1=High, 2=Medium, 3=Low)",
                            "enum": [1, 2, 3],
                        },
                        "assignment_group": {
                            "type": "string",
                            "description": "Assignment group",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Planned start date (YYYY-MM-DD HH:MM:SS)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Planned end date (YYYY-MM-DD HH:MM:SS)",
                        },
                        "custom_fields": {
                            "type": "object",
                            "description": "Additional fields to include in the change request",
                        },
                    },
                    "required": ["short_description", "type"],
                },
            ),
            self._handle_change_create,
        )

        self._register_tool(
            "change_search",
            Tool(
                name="change_search",
                description="Search for change requests",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "description": "Filter by state",
                        },
                        "assignment_group": {
                            "type": "string",
                            "description": "Filter by assignment group",
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category",
                        },
                        "type": {
                            "type": "string",
                            "description": "Filter by change type (normal, standard, emergency)",
                        },
                        "created_after": {
                            "type": "string",
                            "description": "Created after date (YYYY-MM-DD)",
                        },
                        "text_search": {
                            "type": "string",
                            "description": "Search in short description",
                        },
                        "limit": {"type": "integer", "default": 50},
                    },
                },
            ),
            self._handle_change_search,
        )

        self._register_tool(
            "change_update",
            Tool(
                name="change_update",
                description="Update an existing change request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sys_id": {
                            "type": "string",
                            "description": "System ID of the change request",
                        },
                        "work_notes": {
                            "type": "string",
                            "description": "Work notes (internal)",
                        },
                        "state": {
                            "type": "string",
                            "description": "State value",
                        },
                        "assignment_group": {
                            "type": "string",
                            "description": "Assignment group",
                        },
                        "close_code": {
                            "type": "string",
                            "description": "Close code when closing",
                        },
                        "close_notes": {
                            "type": "string",
                            "description": "Close notes",
                        },
                        "custom_fields": {
                            "type": "object",
                            "description": "Additional fields to update",
                        },
                    },
                    "required": ["sys_id"],
                },
            ),
            self._handle_change_update,
        )

        self._register_tool(
            "change_tasks",
            Tool(
                name="change_tasks",
                description="List tasks of a change request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "change_sys_id": {
                            "type": "string",
                            "description": "System ID of the parent change request",
                        },
                        "state": {
                            "type": "string",
                            "description": "Filter by task state",
                        },
                        "limit": {"type": "integer", "default": 20},
                    },
                    "required": ["change_sys_id"],
                },
            ),
            self._handle_change_tasks,
        )

        # CMDB
        self._register_tool(
            "ci_search",
            Tool(
                name="ci_search",
                description="Search for Configuration Items",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "CI name (supports wildcards)",
                        },
                        "class": {
                            "type": "string",
                            "description": "CI class (e.g., cmdb_ci_server, cmdb_ci_appl)",
                        },
                        "operational_status": {
                            "type": "integer",
                            "description": "Operational status (1=Operational, 2=Non-Operational)",
                        },
                        "environment": {
                            "type": "string",
                            "description": "Environment (production, test, development)",
                        },
                        "limit": {"type": "integer", "default": 100},
                    },
                },
            ),
            self._handle_ci_search,
        )

        self._register_tool(
            "ci_relationships",
            Tool(
                name="ci_relationships",
                description="Get relationships for a Configuration Item",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ci_sys_id": {
                            "type": "string",
                            "description": "System ID of the CI",
                        },
                        "type": {
                            "type": "string",
                            "description": "Relationship type filter",
                        },
                    },
                    "required": ["ci_sys_id"],
                },
            ),
            self._handle_ci_relationships,
        )

        # User Management
        self._register_tool(
            "user_search",
            Tool(
                name="user_search",
                description="Search for users",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "User name (first, last, or full)",
                        },
                        "email": {"type": "string", "description": "Email address"},
                        "user_name": {
                            "type": "string",
                            "description": "Username/User ID",
                        },
                        "active": {
                            "type": "boolean",
                            "description": "Filter by active status",
                        },
                        "department": {
                            "type": "string",
                            "description": "Department name",
                        },
                        "limit": {"type": "integer", "default": 50},
                    },
                },
            ),
            self._handle_user_search,
        )

        # Knowledge Base
        self._register_tool(
            "kb_search",
            Tool(
                name="kb_search",
                description="Search knowledge base articles",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "category": {"type": "string", "description": "KB category"},
                        "workflow_state": {
                            "type": "string",
                            "description": "Article state (published, draft, retired)",
                        },
                        "limit": {"type": "integer", "default": 20},
                    },
                    "required": ["query"],
                },
            ),
            self._handle_kb_search,
        )

        # Service Catalog
        self._register_tool(
            "catalog_items",
            Tool(
                name="catalog_items",
                description="List service catalog items",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Catalog category sys_id",
                        },
                        "search": {
                            "type": "string",
                            "description": "Search in item names",
                        },
                        "active": {"type": "boolean", "default": True},
                        "limit": {"type": "integer", "default": 50},
                    },
                },
            ),
            self._handle_catalog_items,
        )

        # RITM (Requested Item) operations
        self._register_tool(
            "ritm_search",
            Tool(
                name="ritm_search",
                description="Search for requested items (RITMs)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "description": "Filter by state",
                        },
                        "cat_item": {
                            "type": "string",
                            "description": "Filter by catalog item sys_id",
                        },
                        "requested_for": {
                            "type": "string",
                            "description": "Filter by requested_for username",
                        },
                        "opened_at": {
                            "type": "string",
                            "description": "Filter opened after date (YYYY-MM-DD)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 50,
                        },
                    },
                },
            ),
            self._handle_ritm_search,
        )

        self._register_tool(
            "ritm_create",
            Tool(
                name="ritm_create",
                description="Order a service catalog item (creates RITM)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cat_item": {
                            "type": "string",
                            "description": "Catalog item sys_id",
                        },
                        "variables": {
                            "type": "object",
                            "description": "Variables for the catalog item",
                        },
                        "requested_for": {
                            "type": "string",
                            "description": "User sys_id to request for",
                        },
                    },
                    "required": ["cat_item"],
                },
            ),
            self._handle_ritm_create,
        )

        # Aggregate operations
        self._register_tool(
            "get_stats",
            Tool(
                name="get_stats",
                description="Get aggregate statistics from a table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                        "group_by": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to group by",
                        },
                        "aggregates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["COUNT", "SUM", "AVG", "MIN", "MAX"],
                                    },
                                    "field": {"type": "string"},
                                    "alias": {"type": "string"},
                                },
                            },
                        },
                        "query": {"type": "string", "description": "Filter query"},
                    },
                    "required": ["table"],
                },
            ),
            self._handle_get_stats,
        )

    def _register_tool(
        self, name: str, tool: Tool, handler: Callable[..., Awaitable[Any]]
    ) -> None:
        """Register a tool with its handler."""
        self._tools[name] = tool
        self._handlers[name] = handler

    # Handler implementations

    async def _handle_query_table(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle table query operation."""
        return await client.query_records(
            table=args["table"],
            query=args.get("query"),
            fields=args.get("fields"),
            limit=args.get("limit", 100),
            offset=args.get("offset", 0),
            order_by=args.get("order_by"),
            display_value="both",
        )

    async def _handle_get_record(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle get record operation."""
        return await client.get_record(
            table=args["table"],
            sys_id=args["sys_id"],
            fields=args.get("fields"),
            display_value="both",
        )

    async def _handle_create_record(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle create record operation."""
        return await client.create_record(
            table=args["table"], data=args["data"], display_value="both"
        )

    async def _handle_update_record(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle update record operation."""
        return await client.update_record(
            table=args["table"],
            sys_id=args["sys_id"],
            data=args["data"],
            display_value="both",
        )

    async def _handle_delete_record(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle delete record operation."""
        success = await client.delete_record(table=args["table"], sys_id=args["sys_id"])
        return {
            "success": success,
            "message": (
                "Record deleted successfully" if success else "Failed to delete record"
            ),
        }

    async def _handle_incident_create(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle incident creation."""
        data = {
            "short_description": args["short_description"],
            "description": args.get("description", ""),
            "urgency": args.get("urgency", 3),
            "impact": args.get("impact", 3),
            "assignment_group": args.get("assignment_group"),
            "assigned_to": args.get("assigned_to"),
            "category": args.get("category"),
            "subcategory": args.get("subcategory"),
        }

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        return await client.create_incident(data, display_value="both")

    async def _handle_incident_update(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle incident update."""
        # First, find the incident by number
        incidents = await client.query_incidents(
            query=f"number={args['number']}", limit=1
        )

        if not incidents:
            return {"error": f"Incident {args['number']} not found"}

        incident = incidents[0]

        # Build update data
        data = {}
        if "state" in args:
            data["state"] = args["state"]
        if "work_notes" in args:
            data["work_notes"] = args["work_notes"]
        if "comments" in args:
            data["comments"] = args["comments"]
        if "resolution_code" in args:
            data["resolution_code"] = args["resolution_code"]
        if "resolution_notes" in args:
            data["resolution_notes"] = args["resolution_notes"]

        return await client.update_incident(
            incident["sys_id"], data, display_value="both"
        )

    async def _handle_incident_search(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle incident search."""
        query_parts = []

        if "assigned_to" in args:
            query_parts.append(f"assigned_to.user_name={args['assigned_to']}")

        if "assignment_group" in args:
            query_parts.append(f"assignment_group.name={args['assignment_group']}")

        if "state" in args:
            states = args["state"]
            if isinstance(states, list):
                state_query = "^OR".join([f"state={s}" for s in states])
                query_parts.append(f"({state_query})")
            else:
                query_parts.append(f"state={states}")

        if "priority" in args:
            priorities = args["priority"]
            if isinstance(priorities, list):
                priority_query = "^OR".join([f"priority={p}" for p in priorities])
                query_parts.append(f"({priority_query})")
            else:
                query_parts.append(f"priority={priorities}")

        if "created_after" in args:
            query_parts.append(f"sys_created_on>{args['created_after']}")

        if "text_search" in args:
            text = args["text_search"]
            query_parts.append(f"short_descriptionLIKE{text}^ORdescriptionLIKE{text}")

        query = "^".join(query_parts) if query_parts else None

        return await client.query_incidents(
            query=query,
            limit=args.get("limit", 50),
            order_by="-sys_created_on",
            display_value="both",
        )

    async def _handle_change_create(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle change request creation."""
        data = {
            "short_description": args["short_description"],
            "description": args.get("description", ""),
            "type": args["type"],
            "risk": args.get("risk", 3),
            "impact": args.get("impact", 3),
            "assignment_group": args.get("assignment_group"),
            "start_date": args.get("start_date"),
            "end_date": args.get("end_date"),
        }

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        # Merge custom fields
        if args.get("custom_fields"):
            data.update(args["custom_fields"])

        return await client.create_record("change_request", data, display_value="both")

    async def _handle_change_search(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle change request search."""
        query_parts = []

        if "state" in args:
            query_parts.append(f"state={args['state']}")

        if "assignment_group" in args:
            query_parts.append(f"assignment_group.name={args['assignment_group']}")

        if "category" in args:
            query_parts.append(f"category={args['category']}")

        if "type" in args:
            query_parts.append(f"type={args['type']}")

        if "created_after" in args:
            query_parts.append(f"sys_created_on>{args['created_after']}")

        if "text_search" in args:
            query_parts.append(f"short_descriptionLIKE{args['text_search']}")

        query = "^".join(query_parts) if query_parts else None

        return await client.query_records(
            "change_request",
            query=query,
            limit=args.get("limit", 50),
            order_by="-sys_created_on",
            display_value="both",
        )

    async def _handle_change_update(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle change request update."""
        sys_id = args["sys_id"]
        data = {}

        if "work_notes" in args:
            data["work_notes"] = args["work_notes"]
        if "state" in args:
            data["state"] = args["state"]
        if "assignment_group" in args:
            data["assignment_group"] = args["assignment_group"]
        if "close_code" in args:
            data["close_code"] = args["close_code"]
        if "close_notes" in args:
            data["close_notes"] = args["close_notes"]
        if "custom_fields" in args:
            data.update(args["custom_fields"])

        return await client.update_record(
            "change_request", sys_id, data, display_value="both"
        )

    async def _handle_change_tasks(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle change task listing."""
        query = f"change_request={args['change_sys_id']}"

        if "state" in args:
            query += f"^state={args['state']}"

        return await client.query_records(
            "change_task",
            query=query,
            limit=args.get("limit", 20),
            order_by="order",
            display_value="both",
        )

    async def _handle_ci_search(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle CI search."""
        query_parts = []

        if "name" in args:
            query_parts.append(f"nameLIKE{args['name']}")

        if "class" in args:
            query_parts.append(f"sys_class_name={args['class']}")

        if "operational_status" in args:
            query_parts.append(f"operational_status={args['operational_status']}")

        if "environment" in args:
            query_parts.append(f"u_environment={args['environment']}")

        query = "^".join(query_parts) if query_parts else None

        # Search across base CMDB table
        return await client.query_records(
            "cmdb_ci", query=query, limit=args.get("limit", 100), display_value="both"
        )

    async def _handle_ci_relationships(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle CI relationship lookup."""
        query = f"parent={args['ci_sys_id']}^ORchild={args['ci_sys_id']}"

        if "type" in args:
            query += f"^type.name={args['type']}"

        relationships = await client.query_records(
            "cmdb_rel_ci", query=query, display_value="both"
        )

        # Enhance with CI details
        for rel in relationships:
            if rel.get("parent") == args["ci_sys_id"]:
                # Get child CI details
                child_ci = await client.get_record("cmdb_ci", rel["child"])
                rel["related_ci"] = child_ci
                rel["direction"] = "outgoing"
            else:
                # Get parent CI details
                parent_ci = await client.get_record("cmdb_ci", rel["parent"])
                rel["related_ci"] = parent_ci
                rel["direction"] = "incoming"

        return relationships

    async def _handle_user_search(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle user search."""
        query_parts = []

        if "name" in args:
            name = args["name"]
            query_parts.append(
                f"first_nameLIKE{name}^ORlast_nameLIKE{name}^ORnameLIKE{name}"
            )

        if "email" in args:
            query_parts.append(f"email={args['email']}")

        if "user_name" in args:
            query_parts.append(f"user_name={args['user_name']}")

        if "active" in args:
            query_parts.append(f"active={str(args['active']).lower()}")

        if "department" in args:
            query_parts.append(f"department.name={args['department']}")

        query = "^".join(query_parts) if query_parts else None

        return await client.query_users(
            query=query,
            limit=args.get("limit", 50),
            fields=[
                "user_name",
                "email",
                "first_name",
                "last_name",
                "department",
                "title",
                "active",
            ],
            display_value="both",
        )

    async def _handle_kb_search(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle knowledge base search."""
        query_parts = []

        # Text search
        if "query" in args:
            text = args["query"]
            query_parts.append(f"short_descriptionLIKE{text}^ORtextLIKE{text}")

        if "category" in args:
            query_parts.append(f"kb_category={args['category']}")

        if "workflow_state" in args:
            query_parts.append(f"workflow_state={args['workflow_state']}")

        query = "^".join(query_parts) if query_parts else None

        return await client.query_records(
            "kb_knowledge",
            query=query,
            limit=args.get("limit", 20),
            order_by="-sys_updated_on",
            fields=[
                "number",
                "short_description",
                "kb_category",
                "workflow_state",
                "author",
                "published",
                "sys_updated_on",
                "view_count",
            ],
            display_value="both",
        )

    async def _handle_catalog_items(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle service catalog item listing."""
        query_parts = []

        if "category" in args:
            query_parts.append(f"category={args['category']}")

        if "search" in args:
            query_parts.append(f"nameLIKE{args['search']}")

        if "active" in args:
            query_parts.append(f"active={str(args['active']).lower()}")

        query = "^".join(query_parts) if query_parts else None

        return await client.query_records(
            "sc_cat_item",
            query=query,
            limit=args.get("limit", 50),
            fields=["name", "short_description", "category", "price", "active"],
            display_value="both",
        )

    async def _handle_get_stats(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle aggregate statistics."""
        return await client.get_aggregate(
            table=args["table"],
            query=args.get("query"),
            group_by=args.get("group_by"),
            aggregate=args.get(
                "aggregates", [{"type": "COUNT", "field": "sys_id", "alias": "count"}]
            ),
        )

    async def _handle_ritm_search(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle RITM search."""
        query_parts = []

        if "state" in args:
            query_parts.append(f"state={args['state']}")

        if "cat_item" in args:
            query_parts.append(f"cat_item={args['cat_item']}")

        if "requested_for" in args:
            query_parts.append(f"requested_for.user_name={args['requested_for']}")

        if "opened_at" in args:
            query_parts.append(f"opened_at>{args['opened_at']}")

        query = "^".join(query_parts) if query_parts else None

        return await client.query_records(
            "sc_req_item",
            query=query,
            limit=args.get("limit", 50),
            order_by="-opened_at",
            display_value="both",
        )

    async def _handle_ritm_create(
        self, client: ServiceNowClient, args: dict[str, Any]
    ) -> Any:
        """Handle RITM creation via service catalog order."""
        return await client.order_catalog_item(
            cat_item=args["cat_item"],
            variables=args.get("variables"),
            requested_for=args.get("requested_for"),
        )
