# World Engine API Documentation

## Overview

World Engine API provides access to the computable model of the book's world. It includes 413 entities, 287 relations, and 55 visual forms across 13 categories.

## Base URL

```
http://localhost:8642/book/world
```

## Endpoints

### GET /summary

Get a brief summary of the world.

**Response:**
```json
{
  "summary": "World Engine: 413 entities...",
  "stats": {
    "world_model": {
      "total_entities": 413,
      "total_categories": 13
    },
    "relation_graph": {
      "total_relations": 287
    }
  }
}
```

### POST /search

Search for entities in the world.

**Request:**
```json
{
  "query": "Аркаим",
  "limit": 10
}
```

**Response:**
```json
{
  "world_model": [...],
  "relations": [...],
  "total": 15
}
```

### GET /entity/{entity_id}

Get a specific entity by ID.

**Parameters:**
- `entity_id` (path, required): Entity ID

**Response:**
```json
{
  "id": "region_arkaim",
  "name": "Аркаим",
  "category": "geography",
  "description": "Ancient settlement...",
  "properties": {...}
}
```

### GET /entity/{entity_id}/context

Get full context of an entity including relations and forms.

**Parameters:**
- `entity_id` (path, required): Entity ID

**Response:**
```json
{
  "entity": {...},
  "relations": {
    "outgoing": [...],
    "incoming": [...],
    "outgoing_count": 10,
    "incoming_count": 9
  }
}
```

### GET /entity/{entity_id}/visual-prompt

Generate a visual prompt for an entity.

**Parameters:**
- `entity_id` (path, required): Entity ID
- `style` (query, optional): Style (cinematic|realistic|watercolor|ethereal)

**Response:**
```json
{
  "entity_id": "region_arkaim",
  "style": "cinematic",
  "prompt": "cinematic fantasy, epic film still..."
}
```

### POST /validate

Validate an entity against world rules.

**Request:**
```json
{
  "entity": {
    "id": "test_event",
    "name": "Test Event",
    "category": "event"
  }
}
```

**Response:**
```json
{
  "is_valid": true,
  "score": 0.95,
  "violations": 0,
  "warnings": 0
}
```

### GET /rules

Get all consistency rules.

**Response:**
```json
{
  "rules": [
    {
      "id": "temporal_no_future",
      "name": "No Future Knowledge",
      "name_ru": "Запрет знания будущего",
      "rule_type": "temporal",
      "severity": "hard"
    }
  ],
  "total": 5
}
```

### GET /modes

Get available experience modes.

**Response:**
```json
{
  "modes": [
    {
      "mode": "dialog",
      "name": "Диалог с книгой",
      "description": "Interactive dialogue..."
    }
  ],
  "total": 10
}
```

### GET /categories

Get all world categories with entity counts.

**Response:**
```json
{
  "categories": {
    "geography": 38,
    "philosophy": 134,
    "language": 134
  },
  "total": 13
}
```

### GET /form-library

Get the visual form library.

**Response:**
```json
{
  "forms": {
    "architecture": [...],
    "clothes": [...],
    "faces": [...]
  },
  "total": 55
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 404 | Entity not found |
| 500 | Internal server error |

## Rate Limits

No rate limits are currently applied.

## Authentication

No authentication required for local development.
