# Individual failing cases

## 01_greetings/recognition--mid_returning--phrase1

Boundary: deterministic; state: mid_returning

```json
{
  "message": "hi",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "hi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 2,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--mid_returning--phrase10

Boundary: deterministic; state: mid_returning

```json
{
  "message": "good morning",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "good morning",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--mid_returning--phrase11

Boundary: deterministic; state: mid_returning

```json
{
  "message": "good evening",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "good evening",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--mid_returning--phrase2

Boundary: deterministic; state: mid_returning

```json
{
  "message": "hello",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "hello",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 5,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--mid_returning--phrase3

Boundary: deterministic; state: mid_returning

```json
{
  "message": "hii",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "hii",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 3,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--mid_returning--phrase4

Boundary: deterministic; state: mid_returning

```json
{
  "message": "helo",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "helo",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 4,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--mid_returning--phrase5

Boundary: deterministic; state: mid_returning

```json
{
  "message": "hey",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "hey",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 3,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--mid_returning--phrase6

Boundary: deterministic; state: mid_returning

```json
{
  "message": "salam",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "salam",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 5,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--mid_returning--phrase7

Boundary: deterministic; state: mid_returning

```json
{
  "message": "salaam",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "salaam",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 6,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--mid_returning--phrase8

Boundary: deterministic; state: mid_returning

```json
{
  "message": "assalam o alaikum",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "assalam o alaikum",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--mid_returning--phrase9

Boundary: deterministic; state: mid_returning

```json
{
  "message": "aoa",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "aoa",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 3,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase1

Boundary: deterministic; state: new

```json
{
  "message": "hi",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "hi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 2,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase10

Boundary: deterministic; state: new

```json
{
  "message": "good morning",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "good morning",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase11

Boundary: deterministic; state: new

```json
{
  "message": "good evening",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "good evening",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase2

Boundary: deterministic; state: new

```json
{
  "message": "hello",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "hello",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 5,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase3

Boundary: deterministic; state: new

```json
{
  "message": "hii",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "hii",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 3,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase4

Boundary: deterministic; state: new

```json
{
  "message": "helo",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "helo",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 4,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase5

Boundary: deterministic; state: new

```json
{
  "message": "hey",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "hey",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 3,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase6

Boundary: deterministic; state: new

```json
{
  "message": "salam",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "salam",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 5,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase7

Boundary: deterministic; state: new

```json
{
  "message": "salaam",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "salaam",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 6,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase8

Boundary: deterministic; state: new

```json
{
  "message": "assalam o alaikum",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "assalam o alaikum",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 01_greetings/recognition--new--phrase9

Boundary: deterministic; state: new

```json
{
  "message": "aoa",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "intent": "greeting"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "aoa",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 3,
    "provider_calls": 1
  },
  "violations": [
    "intent: expected 'greeting', actual 'unknown'"
  ]
}
```

## 03_returning_user/same_city--scope--phrase4

Boundary: http; state: scope

```json
{
  "message": "lahor mein hi",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "DHA",
        "area"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "334ef2c3-5f03-48b5-9dba-1604a0fa3181",
      "message": "Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "pending_scope_confirm": {
        "city": "Lahore"
      },
      "recent_turns": [
        {
          "intent": "unknown",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'DHA'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'"
  ]
}
```

## 03_returning_user/same_city--scope--phrase5

Boundary: http; state: scope

```json
{
  "message": "lahoor hi theek hai",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "DHA",
        "area"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "36004532-0e14-46d0-9bab-55ba43236508",
      "message": "Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "pending_scope_confirm": {
        "city": "Lahore"
      },
      "recent_turns": [
        {
          "intent": "unknown",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'DHA'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'"
  ]
}
```

## 04_search/bedrooms_flexible--known--phrase1

Boundary: repair; state: known

```json
{
  "message": "bedrooms flexible hain",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "bedrooms"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "bedrooms flexible hain",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 22,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'bedrooms'; actual ['area']"
  ]
}
```

## 04_search/bedrooms_flexible--known--phrase2

Boundary: repair; state: known

```json
{
  "message": "rooms adjustable",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "bedrooms"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rooms adjustable",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'bedrooms'; actual []"
  ]
}
```

## 04_search/bedrooms_flexible--known--phrase3

Boundary: repair; state: known

```json
{
  "message": "bedroom koi masla nahi",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "bedrooms"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "bedroom koi masla nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 22,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'bedrooms'; actual []"
  ]
}
```

## 04_search/bedrooms_flexible--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "bedrooms flexible hain",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "bedrooms"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "bedrooms flexible hain",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 22,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'bedrooms'; actual ['area']"
  ]
}
```

## 04_search/bedrooms_flexible--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "rooms adjustable",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "bedrooms"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rooms adjustable",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'bedrooms'; actual []"
  ]
}
```

## 04_search/bedrooms_flexible--mid_returning--phrase3

Boundary: repair; state: mid_returning

```json
{
  "message": "bedroom koi masla nahi",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "bedrooms"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "bedroom koi masla nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 22,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'bedrooms'; actual []"
  ]
}
```

## 04_search/bedrooms_flexible--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "bedrooms flexible hain",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "bedrooms"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "bedrooms flexible hain",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 22,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'bedrooms'; actual ['area']"
  ]
}
```

## 04_search/bedrooms_flexible--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "rooms adjustable",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "bedrooms"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rooms adjustable",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'bedrooms'; actual []"
  ]
}
```

## 04_search/bedrooms_flexible--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "bedroom koi masla nahi",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "bedrooms"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "bedroom koi masla nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 22,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'bedrooms'; actual []"
  ]
}
```

## 04_search/budget_flexible--known--phrase1

Boundary: repair; state: known

```json
{
  "message": "budget koi masla nahi",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "budget"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "budget koi masla nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 21,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'budget'; actual []"
  ]
}
```

## 04_search/budget_flexible--known--phrase2

Boundary: repair; state: known

```json
{
  "message": "budget flexible hai",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "budget"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "budget flexible hai",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 19,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'budget'; actual ['area']"
  ]
}
```

## 04_search/budget_flexible--known--phrase3

Boundary: repair; state: known

```json
{
  "message": "no budget limit",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "budget"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no budget limit",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 15,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'budget'; actual []"
  ]
}
```

## 04_search/budget_flexible--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "budget koi masla nahi",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "budget"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "budget koi masla nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 21,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'budget'; actual []"
  ]
}
```

## 04_search/budget_flexible--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "budget flexible hai",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "budget"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "budget flexible hai",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 19,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'budget'; actual ['area']"
  ]
}
```

## 04_search/budget_flexible--mid_returning--phrase3

Boundary: repair; state: mid_returning

```json
{
  "message": "no budget limit",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "budget"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no budget limit",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 15,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'budget'; actual []"
  ]
}
```

## 04_search/budget_flexible--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "budget koi masla nahi",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "budget"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "budget koi masla nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 21,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'budget'; actual []"
  ]
}
```

## 04_search/budget_flexible--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "budget flexible hai",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "budget"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "budget flexible hai",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 19,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'budget'; actual ['area']"
  ]
}
```

## 04_search/budget_flexible--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "no budget limit",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "budget"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no budget limit",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 15,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'budget'; actual []"
  ]
}
```

## 04_search/type_flexible--known--phrase1

Boundary: repair; state: known

```json
{
  "message": "property type koi bhi",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "property_type"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "property type koi bhi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 21,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'property_type'; actual ['area']"
  ]
}
```

## 04_search/type_flexible--known--phrase2

Boundary: repair; state: known

```json
{
  "message": "any property type",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "property_type"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "any property type",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'property_type'; actual []"
  ]
}
```

## 04_search/type_flexible--known--phrase3

Boundary: repair; state: known

```json
{
  "message": "type flexible hai",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "property_type"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "type flexible hai",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'property_type'; actual ['area']"
  ]
}
```

## 04_search/type_flexible--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "property type koi bhi",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "property_type"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "property type koi bhi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 21,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'property_type'; actual ['area']"
  ]
}
```

## 04_search/type_flexible--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "any property type",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "property_type"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "any property type",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'property_type'; actual []"
  ]
}
```

## 04_search/type_flexible--mid_returning--phrase3

Boundary: repair; state: mid_returning

```json
{
  "message": "type flexible hai",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "property_type"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "type flexible hai",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'property_type'; actual ['area']"
  ]
}
```

## 04_search/type_flexible--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "property type koi bhi",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "property_type"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "property type koi bhi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 21,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'property_type'; actual ['area']"
  ]
}
```

## 04_search/type_flexible--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "any property type",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "property_type"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "any property type",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'property_type'; actual []"
  ]
}
```

## 04_search/type_flexible--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "type flexible hai",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "relax": [
        "property_type"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [
      "area"
    ],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "type flexible hai",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "relax: missing 'property_type'; actual ['area']"
  ]
}
```

## 05_location/city_typo--known--phrase1

Boundary: repair; state: known

```json
{
  "message": "lahor",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.city": "Lahore"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "lahor",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 5,
    "provider_calls": 1
  },
  "violations": [
    "required.city: expected 'Lahore', actual None"
  ]
}
```

## 05_location/city_typo--known--phrase2

Boundary: repair; state: known

```json
{
  "message": "lahoor mein",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.city": "Lahore"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "lahoor mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.city: expected 'Lahore', actual None"
  ]
}
```

## 05_location/city_typo--known--phrase3

Boundary: repair; state: known

```json
{
  "message": "Lahroe mein property",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.city": "Lahore"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Lahroe mein property",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 20,
    "provider_calls": 1
  },
  "violations": [
    "required.city: expected 'Lahore', actual None"
  ]
}
```

## 05_location/city_typo--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "lahor",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.city": "Lahore"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "lahor",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 5,
    "provider_calls": 1
  },
  "violations": [
    "required.city: expected 'Lahore', actual None"
  ]
}
```

## 05_location/city_typo--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "lahoor mein",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.city": "Lahore"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "lahoor mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.city: expected 'Lahore', actual None"
  ]
}
```

## 05_location/city_typo--mid_returning--phrase3

Boundary: repair; state: mid_returning

```json
{
  "message": "Lahroe mein property",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.city": "Lahore"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Lahroe mein property",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 20,
    "provider_calls": 1
  },
  "violations": [
    "required.city: expected 'Lahore', actual None"
  ]
}
```

## 05_location/city_typo--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "lahor",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.city": "Lahore"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "lahor",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 5,
    "provider_calls": 1
  },
  "violations": [
    "required.city: expected 'Lahore', actual None"
  ]
}
```

## 05_location/city_typo--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "lahoor mein",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.city": "Lahore"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "lahoor mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.city: expected 'Lahore', actual None"
  ]
}
```

## 05_location/city_typo--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "Lahroe mein property",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.city": "Lahore"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Lahroe mein property",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 20,
    "provider_calls": 1
  },
  "violations": [
    "required.city: expected 'Lahore', actual None"
  ]
}
```

## 05_location/correction--known--phrase1

Boundary: repair; state: known

```json
{
  "message": "Bahria mein sorry DHA mein",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "Bahria"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Bahria mein sorry DHA mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 26,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA', actual 'Bahria'"
  ]
}
```

## 05_location/correction--known--phrase2

Boundary: repair; state: known

```json
{
  "message": "Bahria nahi DHA chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "Bahria"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Bahria nahi DHA chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 23,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA', actual 'Bahria'"
  ]
}
```

## 05_location/correction--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "Bahria mein sorry DHA mein",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "Bahria"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Bahria mein sorry DHA mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 26,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA', actual 'Bahria'"
  ]
}
```

## 05_location/correction--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "Bahria nahi DHA chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "Bahria"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Bahria nahi DHA chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 23,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA', actual 'Bahria'"
  ]
}
```

## 05_location/correction--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "Bahria mein sorry DHA mein",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "Bahria"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Bahria mein sorry DHA mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 26,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA', actual 'Bahria'"
  ]
}
```

## 05_location/correction--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "Bahria nahi DHA chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "Bahria"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Bahria nahi DHA chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 23,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA', actual 'Bahria'"
  ]
}
```

## 05_location/full_phase--known--phrase1

Boundary: repair; state: known

```json
{
  "message": "DHA Phase 5",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA Phase 5"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA Phase 5",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA Phase 5', actual 'DHA'"
  ]
}
```

## 05_location/full_phase--known--phrase2

Boundary: repair; state: known

```json
{
  "message": "DHA Phase 5 mein",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA Phase 5"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA Phase 5 mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA Phase 5', actual 'DHA'"
  ]
}
```

## 05_location/full_phase--known--phrase3

Boundary: repair; state: known

```json
{
  "message": "show DHA Phase 5",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA Phase 5"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "show DHA Phase 5",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA Phase 5', actual 'DHA'"
  ]
}
```

## 05_location/full_phase--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "DHA Phase 5",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA Phase 5"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA Phase 5",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA Phase 5', actual 'DHA'"
  ]
}
```

## 05_location/full_phase--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "DHA Phase 5 mein",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA Phase 5"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA Phase 5 mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA Phase 5', actual 'DHA'"
  ]
}
```

## 05_location/full_phase--mid_returning--phrase3

Boundary: repair; state: mid_returning

```json
{
  "message": "show DHA Phase 5",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA Phase 5"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "show DHA Phase 5",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA Phase 5', actual 'DHA'"
  ]
}
```

## 05_location/full_phase--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "DHA Phase 5",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA Phase 5"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA Phase 5",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA Phase 5', actual 'DHA'"
  ]
}
```

## 05_location/full_phase--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "DHA Phase 5 mein",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA Phase 5"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA Phase 5 mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA Phase 5', actual 'DHA'"
  ]
}
```

## 05_location/full_phase--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "show DHA Phase 5",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.area": "DHA Phase 5"
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "show DHA Phase 5",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "required.area: expected 'DHA Phase 5', actual 'DHA'"
  ]
}
```

## 05_location/multiple--known--phrase3

Boundary: http; state: known

```json
{
  "message": "DHA mein dikhao",
  "effective_context": {
    "saved_before": {},
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "required": {
        "area": "DHA"
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "DHA Phase 5",
        "DHA Phase 6",
        "kis phase"
      ]
    },
    "empty": [
      "response.properties"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "5695bb1d-ca76-40b1-bb0b-afc023164999",
      "message": "Theek hai! DHA Phase 5 mein ye verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.",
      "recommendation_session_id": "659bd77e-3be0-46d1-b793-ad4189412515",
      "properties": [
        {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "DHA",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        },
        {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      ],
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "659bd77e-3be0-46d1-b793-ad4189412515",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA Phase 5",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "659bd77e-3be0-46d1-b793-ad4189412515",
        "property_id": "P-2",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA Phase 5",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "city": "Lahore",
          "area": "DHA",
          "price": 12000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      },
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "659bd77e-3be0-46d1-b793-ad4189412515",
        "property_id": "P-1",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA Phase 5",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA Phase 5",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {},
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'DHA Phase 6'; actual 'Theek hai! DHA Phase 5 mein ye verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.message: missing 'kis phase'; actual 'Theek hai! DHA Phase 5 mein ye verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.properties: expected empty, actual [{'property_id': 'P-2', 'property_name': 'Home P-2', 'city': 'Lahore', 'area': 'DHA', 'price': 12000000.0, 'currency': 'PKR', 'bedrooms': 3, 'bathrooms': 2, 'property_type': 'Apartment', 'purpose': 'purchase', 'amenities': ['Parking'], 'available': True, 'status': 'Ready'}, {'property_id': 'P-1', 'property_name': 'Home P-1', 'city': 'Lahore', 'area': 'DHA', 'price': 10000000.0, 'currency': 'PKR', 'bedrooms': 3, 'bathrooms': 2, 'property_type': 'Apartment', 'purpose': 'purchase', 'amenities': ['Parking'], 'available': True, 'status': 'Ready'}]"
  ]
}
```

## 05_location/multiple--shown--phrase3

Boundary: http; state: shown

```json
{
  "message": "DHA mein dikhao",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "60b71661-aef7-4150-8e5b-cf812913614b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "required": {
        "area": "DHA"
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "DHA Phase 5",
        "DHA Phase 6",
        "kis phase"
      ]
    },
    "empty": [
      "response.properties"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "e0cace09-9631-42bb-8562-e3e68a59375a",
      "message": "Theek hai! DHA Phase 5 mein ye verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.",
      "recommendation_session_id": "649247c4-bfcd-45bb-9785-0aea0fb113d3",
      "properties": [
        {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "DHA",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        },
        {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      ],
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "649247c4-bfcd-45bb-9785-0aea0fb113d3",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA Phase 5",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "649247c4-bfcd-45bb-9785-0aea0fb113d3",
        "property_id": "P-2",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA Phase 5",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "city": "Lahore",
          "area": "DHA",
          "price": 12000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      },
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "649247c4-bfcd-45bb-9785-0aea0fb113d3",
        "property_id": "P-1",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA Phase 5",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA Phase 5",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "60b71661-aef7-4150-8e5b-cf812913614b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'DHA Phase 6'; actual 'Theek hai! DHA Phase 5 mein ye verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.message: missing 'kis phase'; actual 'Theek hai! DHA Phase 5 mein ye verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.properties: expected empty, actual [{'property_id': 'P-2', 'property_name': 'Home P-2', 'city': 'Lahore', 'area': 'DHA', 'price': 12000000.0, 'currency': 'PKR', 'bedrooms': 3, 'bathrooms': 2, 'property_type': 'Apartment', 'purpose': 'purchase', 'amenities': ['Parking'], 'available': True, 'status': 'Ready'}, {'property_id': 'P-1', 'property_name': 'Home P-1', 'city': 'Lahore', 'area': 'DHA', 'price': 10000000.0, 'currency': 'PKR', 'bedrooms': 3, 'bathrooms': 2, 'property_type': 'Apartment', 'purpose': 'purchase', 'amenities': ['Parking'], 'available': True, 'status': 'Ready'}]"
  ]
}
```

## 05_location/phase_without_parent--mid_new--phrase1

Boundary: repair; state: mid_new

```json
{
  "message": "Phase 5",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "needs_clarification": true
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "Phase 5"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Phase 5",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 7,
    "provider_calls": 1
  },
  "violations": [
    "needs_clarification: expected True, actual False"
  ]
}
```

## 05_location/phase_without_parent--mid_new--phrase2

Boundary: repair; state: mid_new

```json
{
  "message": "Phase 5 mein",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "needs_clarification": true
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "Phase 5"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Phase 5 mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "needs_clarification: expected True, actual False"
  ]
}
```

## 05_location/phase_without_parent--mid_new--phrase3

Boundary: repair; state: mid_new

```json
{
  "message": "phase 5 only",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "needs_clarification": true
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "phase 5"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "phase 5 only",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "needs_clarification: expected True, actual False"
  ]
}
```

## 05_location/phase_without_parent--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "Phase 5",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "needs_clarification": true
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "Phase 5"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Phase 5",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 7,
    "provider_calls": 1
  },
  "violations": [
    "needs_clarification: expected True, actual False"
  ]
}
```

## 05_location/phase_without_parent--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "Phase 5 mein",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "needs_clarification": true
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "Phase 5"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "Phase 5 mein",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "needs_clarification: expected True, actual False"
  ]
}
```

## 05_location/phase_without_parent--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "phase 5 only",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "needs_clarification": true
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "phase 5"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "phase 5 only",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "needs_clarification: expected True, actual False"
  ]
}
```

## 06_budget/booking_budget--selected--phrase1

Boundary: http; state: selected

```json
{
  "message": "budget flexible hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "d4c544fb-0f7e-4c49-a0ac-d57aa752245d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-2"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "preserve_prefs": true,
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "858973ca-b2eb-41b5-9eea-a1e83e684134",
      "message": "Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.",
      "recommendation_session_id": "99d4aeca-a83c-484f-b2f9-98a2a884a108",
      "properties": [
        {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "DHA",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        },
        {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      ],
      "requires_clarification": false
    },
    "saved": {
      "flexible": [
        "budget"
      ],
      "excluded": {},
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ],
      "recommendation_session_id": "99d4aeca-a83c-484f-b2f9-98a2a884a108",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": null,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "99d4aeca-a83c-484f-b2f9-98a2a884a108",
        "property_id": "P-2",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": null,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "city": "Lahore",
          "area": "DHA",
          "price": 12000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      },
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "99d4aeca-a83c-484f-b2f9-98a2a884a108",
        "property_id": "P-1",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": null,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      },
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": null,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": null,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "d4c544fb-0f7e-4c49-a0ac-d57aa752245d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-2"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'date'; actual 'Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.message: missing 'time'; actual 'Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.properties: expected empty, actual [{'property_id': 'P-2', 'property_name': 'Home P-2', 'city': 'Lahore', 'area': 'DHA', 'price': 12000000.0, 'currency': 'PKR', 'bedrooms': 3, 'bathrooms': 2, 'property_type': 'Apartment', 'purpose': 'purchase', 'amenities': ['Parking'], 'available': True, 'status': 'Ready'}, {'property_id': 'P-1', 'property_name': 'Home P-1', 'city': 'Lahore', 'area': 'DHA', 'price': 10000000.0, 'currency': 'PKR', 'bedrooms': 3, 'bathrooms': 2, 'property_type': 'Apartment', 'purpose': 'purchase', 'amenities': ['Parking'], 'available': True, 'status': 'Ready'}]",
    "preferences changed during unrelated/pending interaction"
  ]
}
```

## 06_budget/booking_budget--selected--phrase2

Boundary: http; state: selected

```json
{
  "message": "budget koi masla nahi",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4c0375dc-06d3-4ee4-9476-658d8b3e192e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-2"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "preserve_prefs": true,
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "e8fb3a76-1862-4778-b170-96a83b867c48",
      "message": "Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.",
      "recommendation_session_id": "58a907c5-f2cd-4929-953c-6433ca20af7d",
      "properties": [
        {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "DHA",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        },
        {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      ],
      "requires_clarification": false
    },
    "saved": {
      "flexible": [
        "budget"
      ],
      "excluded": {},
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ],
      "recommendation_session_id": "58a907c5-f2cd-4929-953c-6433ca20af7d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": null,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "58a907c5-f2cd-4929-953c-6433ca20af7d",
        "property_id": "P-2",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": null,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "city": "Lahore",
          "area": "DHA",
          "price": 12000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      },
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "58a907c5-f2cd-4929-953c-6433ca20af7d",
        "property_id": "P-1",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": null,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      },
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": null,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": null,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4c0375dc-06d3-4ee4-9476-658d8b3e192e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-2"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'date'; actual 'Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.message: missing 'time'; actual 'Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.properties: expected empty, actual [{'property_id': 'P-2', 'property_name': 'Home P-2', 'city': 'Lahore', 'area': 'DHA', 'price': 12000000.0, 'currency': 'PKR', 'bedrooms': 3, 'bathrooms': 2, 'property_type': 'Apartment', 'purpose': 'purchase', 'amenities': ['Parking'], 'available': True, 'status': 'Ready'}, {'property_id': 'P-1', 'property_name': 'Home P-1', 'city': 'Lahore', 'area': 'DHA', 'price': 10000000.0, 'currency': 'PKR', 'bedrooms': 3, 'bathrooms': 2, 'property_type': 'Apartment', 'purpose': 'purchase', 'amenities': ['Parking'], 'available': True, 'status': 'Ready'}]",
    "preferences changed during unrelated/pending interaction"
  ]
}
```

## 06_budget/booking_budget--selected--phrase3

Boundary: http; state: selected

```json
{
  "message": "ab budget 3 crore",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "79eee0e5-74c0-4568-b5c1-cf4cf1fa91d9",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-2"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "preserve_prefs": true,
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "6f7957b0-d0af-40e0-bda3-ae0b840bac35",
      "message": "Ji, aapki preferences update ho gayi hain.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 30000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "79eee0e5-74c0-4568-b5c1-cf4cf1fa91d9",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-2"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'time'; actual 'Ji, aapki preferences update ho gayi hain.'",
    "preferences changed during unrelated/pending interaction"
  ]
}
```

## 06_budget/booking_budget--single--phrase1

Boundary: http; state: single

```json
{
  "message": "budget flexible hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "28140edb-1cff-4974-8d10-818481f0afb7",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-1"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "preserve_prefs": true,
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "4cc17371-e3d3-441c-b750-f6fea8ad839d",
      "message": "Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.",
      "recommendation_session_id": "c9e4f092-4ea9-417d-acb0-9f5e43561914",
      "properties": [
        {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      ],
      "requires_clarification": false
    },
    "saved": {
      "flexible": [
        "budget"
      ],
      "excluded": {},
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ],
      "recommendation_session_id": "c9e4f092-4ea9-417d-acb0-9f5e43561914",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": null,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "c9e4f092-4ea9-417d-acb0-9f5e43561914",
        "property_id": "P-1",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": null,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      },
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": null,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": null,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "28140edb-1cff-4974-8d10-818481f0afb7",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-1"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'date'; actual 'Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.message: missing 'time'; actual 'Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.properties: expected empty, actual [{'property_id': 'P-1', 'property_name': 'Home P-1', 'city': 'Lahore', 'area': 'DHA', 'price': 10000000.0, 'currency': 'PKR', 'bedrooms': 3, 'bathrooms': 2, 'property_type': 'Apartment', 'purpose': 'purchase', 'amenities': ['Parking'], 'available': True, 'status': 'Ready'}]",
    "preferences changed during unrelated/pending interaction"
  ]
}
```

## 06_budget/booking_budget--single--phrase2

Boundary: http; state: single

```json
{
  "message": "budget koi masla nahi",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "6348d31c-2cb6-42be-889d-086d6bf0b991",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-1"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "preserve_prefs": true,
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "d43c3145-0578-4174-920f-f1e6d8143c8a",
      "message": "Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.",
      "recommendation_session_id": "6b14c4b7-2184-465f-be5d-a0067e94f436",
      "properties": [
        {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      ],
      "requires_clarification": false
    },
    "saved": {
      "flexible": [
        "budget"
      ],
      "excluded": {},
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ],
      "recommendation_session_id": "6b14c4b7-2184-465f-be5d-a0067e94f436",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": null,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "6b14c4b7-2184-465f-be5d-a0067e94f436",
        "property_id": "P-1",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": null,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      },
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": null,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": null,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "6348d31c-2cb6-42be-889d-086d6bf0b991",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-1"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'date'; actual 'Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.message: missing 'time'; actual 'Ji! Aapke criteria ke mutabiq filhaal ye behtareen verified options available hain: 1. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'",
    "response.properties: expected empty, actual [{'property_id': 'P-1', 'property_name': 'Home P-1', 'city': 'Lahore', 'area': 'DHA', 'price': 10000000.0, 'currency': 'PKR', 'bedrooms': 3, 'bathrooms': 2, 'property_type': 'Apartment', 'purpose': 'purchase', 'amenities': ['Parking'], 'available': True, 'status': 'Ready'}]",
    "preferences changed during unrelated/pending interaction"
  ]
}
```

## 06_budget/booking_budget--single--phrase3

Boundary: http; state: single

```json
{
  "message": "ab budget 3 crore",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "97edba8e-0bdb-4089-ac0f-8b9e7a88d7df",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-1"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "preserve_prefs": true,
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "8369c77c-f708-48fb-a258-36e29ab49a1f",
      "message": "Ji, aapki preferences update ho gayi hain.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 30000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "97edba8e-0bdb-4089-ac0f-8b9e7a88d7df",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": {
        "intent": "schedule_visit",
        "property_id": "P-1"
      },
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'time'; actual 'Ji, aapki preferences update ho gayi hain.'",
    "preferences changed during unrelated/pending interaction"
  ]
}
```

## 06_budget/decimal_1--known--phrase1

Boundary: repair; state: known

```json
{
  "message": "budget 3.5m",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.budget": 3500000,
      "preferred.budget": null
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "budget 3.5m",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.budget: expected 3500000, actual None"
  ]
}
```

## 06_budget/decimal_1--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "budget 3.5m",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.budget": 3500000,
      "preferred.budget": null
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "budget 3.5m",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.budget: expected 3500000, actual None"
  ]
}
```

## 06_budget/decimal_1--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "budget 3.5m",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.budget": 3500000,
      "preferred.budget": null
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "budget 3.5m",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.budget: expected 3500000, actual None"
  ]
}
```

## 06_budget/unknown_purpose--mid_new--phrase5

Boundary: repair; state: mid_new

```json
{
  "message": "3.5m",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "needs_clarification": true,
      "clarification_reason": "missing_purpose_for_budget"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "3.5m",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 4,
    "provider_calls": 1
  },
  "violations": [
    "needs_clarification: expected True, actual False",
    "clarification_reason: expected 'missing_purpose_for_budget', actual None"
  ]
}
```

## 06_budget/unknown_purpose--new--phrase5

Boundary: repair; state: new

```json
{
  "message": "3.5m",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "needs_clarification": true,
      "clarification_reason": "missing_purpose_for_budget"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "3.5m",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 4,
    "provider_calls": 1
  },
  "violations": [
    "needs_clarification: expected True, actual False",
    "clarification_reason: expected 'missing_purpose_for_budget', actual None"
  ]
}
```

## 07_attributes/house--known--phrase2

Boundary: repair; state: known

```json
{
  "message": "ghar chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.property_type": "House"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "ghar chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "required.property_type: expected 'House', actual None"
  ]
}
```

## 07_attributes/house--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "ghar chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "eq": {
      "required.property_type": "House"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "ghar chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "required.property_type: expected 'House', actual None"
  ]
}
```

## 07_attributes/negative_amenity--known--phrase1

Boundary: repair; state: known

```json
{
  "message": "gym nahi chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "gym nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 07_attributes/negative_amenity--known--phrase2

Boundary: repair; state: known

```json
{
  "message": "no gym please",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no gym please",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 13,
    "provider_calls": 1
  },
  "violations": [
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 07_attributes/negative_amenity--known--phrase3

Boundary: repair; state: known

```json
{
  "message": "gym ke baghair",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "gym ke baghair",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 14,
    "provider_calls": 1
  },
  "violations": [
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 07_attributes/negative_amenity--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "gym nahi chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "gym nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 07_attributes/negative_amenity--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "no gym please",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no gym please",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 13,
    "provider_calls": 1
  },
  "violations": [
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 07_attributes/negative_amenity--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "gym ke baghair",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "gym ke baghair",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 14,
    "provider_calls": 1
  },
  "violations": [
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 08_feedback/liked--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "pehli pasand hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "3790ed97-9e47-4e1c-aead-b6c202fbcf15",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "b4843c80-3de0-4bfb-8018-178268a22364",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "3790ed97-9e47-4e1c-aead-b6c202fbcf15",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "3790ed97-9e47-4e1c-aead-b6c202fbcf15",
        "property_id": "P-2",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "3790ed97-9e47-4e1c-aead-b6c202fbcf15",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 08_feedback/liked--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "first option achi hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "2528313d-06d7-4812-b18d-81d4722208c9",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "4d9f8645-9bb8-4095-959d-e2b607cff8a7",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "2528313d-06d7-4812-b18d-81d4722208c9",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "2528313d-06d7-4812-b18d-81d4722208c9",
        "property_id": "P-2",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "2528313d-06d7-4812-b18d-81d4722208c9",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 08_feedback/liked--filtered--phrase3

Boundary: http; state: filtered

```json
{
  "message": "option 1 like kar dein",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "21ceed9b-faad-4d19-9119-e7d4d4405e79",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "109d0c75-e3ba-4a5c-a96b-2d748da0f208",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "21ceed9b-faad-4d19-9119-e7d4d4405e79",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "21ceed9b-faad-4d19-9119-e7d4d4405e79",
        "property_id": "P-2",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "21ceed9b-faad-4d19-9119-e7d4d4405e79",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 08_feedback/rejected--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "pehli reject kar dein",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "155abff1-57c0-4cec-98d3-486accf7b20d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "rejected",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "acf083be-c791-49a0-bb7b-fcecf361ba87",
      "message": "Theek hai, yeh option reject kar diya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "155abff1-57c0-4cec-98d3-486accf7b20d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "rejected",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "155abff1-57c0-4cec-98d3-486accf7b20d",
        "property_id": "P-2",
        "action": "rejected",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "155abff1-57c0-4cec-98d3-486accf7b20d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 08_feedback/rejected--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "first option nahi chahiye",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "76289405-5a0b-4b9d-8fa9-47e9ff65b48d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "rejected",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "3bf2f1e9-4d03-414a-bbef-d71975867201",
      "message": "Theek hai, yeh option reject kar diya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "76289405-5a0b-4b9d-8fa9-47e9ff65b48d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "rejected",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "76289405-5a0b-4b9d-8fa9-47e9ff65b48d",
        "property_id": "P-2",
        "action": "rejected",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "76289405-5a0b-4b9d-8fa9-47e9ff65b48d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 08_feedback/rejected--filtered--phrase3

Boundary: http; state: filtered

```json
{
  "message": "option 1 hata dein",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9436f9fd-1eae-4b73-ad89-11ef8b5c7cbe",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "rejected",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "a74fcc13-5f4b-4880-be42-2920f824169c",
      "message": "Theek hai, yeh option reject kar diya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9436f9fd-1eae-4b73-ad89-11ef8b5c7cbe",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "rejected",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "9436f9fd-1eae-4b73-ad89-11ef8b5c7cbe",
        "property_id": "P-2",
        "action": "rejected",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9436f9fd-1eae-4b73-ad89-11ef8b5c7cbe",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 08_feedback/shortlisted--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "pehli shortlist kar dein",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "8127456b-4d3c-4231-b4b2-2f360998994d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "shortlisted",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "8f991822-6464-4866-afcb-268b07dd8306",
      "message": "Ji, yeh property shortlist kar li hai.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "8127456b-4d3c-4231-b4b2-2f360998994d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "shortlisted",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "8127456b-4d3c-4231-b4b2-2f360998994d",
        "property_id": "P-2",
        "action": "shortlisted",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "8127456b-4d3c-4231-b4b2-2f360998994d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 08_feedback/shortlisted--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "first option save kar lein",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "740df980-99e7-40ea-a71c-a1695348297f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "shortlisted",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "459630bd-66cb-4ab6-aefb-465e5f1a279c",
      "message": "Ji, yeh property shortlist kar li hai.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "740df980-99e7-40ea-a71c-a1695348297f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "shortlisted",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "740df980-99e7-40ea-a71c-a1695348297f",
        "property_id": "P-2",
        "action": "shortlisted",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "740df980-99e7-40ea-a71c-a1695348297f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 08_feedback/shortlisted--filtered--phrase3

Boundary: http; state: filtered

```json
{
  "message": "option 1 shortlist please",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9eda62ad-c854-45e2-9dc0-ebfd3bb7dcfb",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "shortlisted",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "c3cc6fff-a518-4b29-9ccb-2b1f7bbb3405",
      "message": "Ji, yeh property shortlist kar li hai.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9eda62ad-c854-45e2-9dc0-ebfd3bb7dcfb",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "shortlisted",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "9eda62ad-c854-45e2-9dc0-ebfd3bb7dcfb",
        "property_id": "P-2",
        "action": "shortlisted",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9eda62ad-c854-45e2-9dc0-ebfd3bb7dcfb",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 09_booking/full--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "pehli ki visit 2 January 2030 subah 10 baje",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0b7faa1f-6a74-43fb-8deb-7b58ddd43815",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0,
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "booked_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "response.appointment",
      "appointments"
    ],
    "empty": [
      "saved.pending_action"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "11893d14-42db-49ad-940c-89e61f78b300",
      "message": "Ji, appointment request confirm ho gayi. Appointments page par details dekh sakte hain.",
      "appointment": {
        "appointment_id": "3ec0643b-c3d8-4cf1-9f97-a4ca86a322fd",
        "status": "confirmed"
      },
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0b7faa1f-6a74-43fb-8deb-7b58ddd43815",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [
      [
        "POST",
        "/appointments",
        {
          "client_name": "Ali",
          "client_phone": "+923001234567",
          "client_email": "ali@example.com",
          "employee_name": "Sara AI Agent",
          "employee_email": "sara@realestatehub.pk",
          "property_id": "P-2",
          "property_name": "Home P-2",
          "starts_at": "2030-01-02T10:00:00+05:00",
          "duration_minutes": 60,
          "meeting_notes": ""
        }
      ]
    ],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0b7faa1f-6a74-43fb-8deb-7b58ddd43815",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": [
      "P-2"
    ]
  },
  "violations": [
    "booked_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 09_booking/full--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "book first option for 2 Jan 2030 at 10am Pakistan time",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0ad9124f-fcef-43d1-9090-947211fce8b2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0,
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "booked_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "response.appointment",
      "appointments"
    ],
    "empty": [
      "saved.pending_action"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "a44fb5cf-a146-44c4-84e2-90b463c03258",
      "message": "Ji, appointment request confirm ho gayi. Appointments page par details dekh sakte hain.",
      "appointment": {
        "appointment_id": "32fe8028-8d18-4d9a-9912-695fbfa7d545",
        "status": "confirmed"
      },
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0ad9124f-fcef-43d1-9090-947211fce8b2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [
      [
        "POST",
        "/appointments",
        {
          "client_name": "Ali",
          "client_phone": "+923001234567",
          "client_email": "ali@example.com",
          "employee_name": "Sara AI Agent",
          "employee_email": "sara@realestatehub.pk",
          "property_id": "P-2",
          "property_name": "Home P-2",
          "starts_at": "2030-01-02T10:00:00+05:00",
          "duration_minutes": 60,
          "meeting_notes": ""
        }
      ]
    ],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0ad9124f-fcef-43d1-9090-947211fce8b2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": [
      "P-2"
    ]
  },
  "violations": [
    "booked_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 09_booking/full--filtered--phrase3

Boundary: http; state: filtered

```json
{
  "message": "option 1 visit 2030-01-02 10:00 PKT",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "51b65924-0f95-43bb-884f-7ca26a8c3451",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0,
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "booked_ids": [
        "P-1"
      ]
    },
    "truthy": [
      "response.appointment",
      "appointments"
    ],
    "empty": [
      "saved.pending_action"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "726f88d2-1ce8-4707-8944-f89408044812",
      "message": "Ji, appointment request confirm ho gayi. Appointments page par details dekh sakte hain.",
      "appointment": {
        "appointment_id": "23fc4441-93cd-4376-b72f-e1e1e1350e4e",
        "status": "confirmed"
      },
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "51b65924-0f95-43bb-884f-7ca26a8c3451",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [
      [
        "POST",
        "/appointments",
        {
          "client_name": "Ali",
          "client_phone": "+923001234567",
          "client_email": "ali@example.com",
          "employee_name": "Sara AI Agent",
          "employee_email": "sara@realestatehub.pk",
          "property_id": "P-2",
          "property_name": "Home P-2",
          "starts_at": "2030-01-02T10:00:00+05:00",
          "duration_minutes": 60,
          "meeting_notes": ""
        }
      ]
    ],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "51b65924-0f95-43bb-884f-7ca26a8c3451",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": [
      "P-2"
    ]
  },
  "violations": [
    "booked_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 09_booking/single_time--single--phrase1

Boundary: http; state: single

```json
{
  "message": "2 January 2030 subah 10 baje visit",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "2d7a125f-eae6-476c-9dea-96a344ec7e5e",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200
    },
    "truthy": [
      "response.appointment"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "972117ff-a06c-423f-aa04-8a0c315e2829",
      "message": "Kis property ka visit book karna hai? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "2d7a125f-eae6-476c-9dea-96a344ec7e5e",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": {
        "intent": "schedule_visit"
      },
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "2d7a125f-eae6-476c-9dea-96a344ec7e5e",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.appointment: expected nonempty, actual None"
  ]
}
```

## 09_booking/single_time--single--phrase2

Boundary: http; state: single

```json
{
  "message": "visit tomorrow at 10 PKT",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "459028a0-1b76-4d4a-a665-9943a3234c00",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200
    },
    "truthy": [
      "response.appointment"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "68274947-6b46-4a99-8747-c1384636259a",
      "message": "Kis property ka visit book karna hai? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "459028a0-1b76-4d4a-a665-9943a3234c00",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": {
        "intent": "schedule_visit"
      },
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "459028a0-1b76-4d4a-a665-9943a3234c00",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.appointment: expected nonempty, actual None"
  ]
}
```

## 09_booking/single_time--single--phrase3

Boundary: http; state: single

```json
{
  "message": "kal 10 baje visit karni hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "20872325-d608-4fb8-92e7-a035e1632a4c",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200
    },
    "truthy": [
      "response.appointment"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "5564ea63-3e6b-40ba-931f-5104d7e87e2f",
      "message": "Kis property ka visit book karna hai? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "20872325-d608-4fb8-92e7-a035e1632a4c",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": {
        "intent": "schedule_visit"
      },
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "20872325-d608-4fb8-92e7-a035e1632a4c",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.appointment: expected nonempty, actual None"
  ]
}
```

## 10_details/amenities--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "amenities kya hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e61b0cf0-abd1-42e5-a78b-1a371df929b1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Parking",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "4a974f9a-80ed-4c73-8e7e-caac8cfeaa61",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e61b0cf0-abd1-42e5-a78b-1a371df929b1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e61b0cf0-abd1-42e5-a78b-1a371df929b1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Parking'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/amenities--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "facilities kya hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "85d6dc4f-c468-4adb-9b23-218fa0f71d8f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Parking",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "c9bc671f-37b5-4a31-b754-c6c5b2537ef8",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "85d6dc4f-c468-4adb-9b23-218fa0f71d8f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "85d6dc4f-c468-4adb-9b23-218fa0f71d8f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Parking'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/area_attribute--shown--phrase1

Boundary: http; state: shown

```json
{
  "message": "DHA mein price kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9e3dcb0a-f360-4fa0-bc07-823dddba46d4",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "04598fc9-5e21-4979-96bd-03176a69f0f0",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9e3dcb0a-f360-4fa0-bc07-823dddba46d4",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9e3dcb0a-f360-4fa0-bc07-823dddba46d4",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/area_attribute--shown--phrase2

Boundary: http; state: shown

```json
{
  "message": "DHA mein amenities kya hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0c4b80de-1dda-459e-8ad2-21a82764e24a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "c7511a09-efa9-40ba-b379-0e7148d80c0f",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0c4b80de-1dda-459e-8ad2-21a82764e24a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0c4b80de-1dda-459e-8ad2-21a82764e24a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/area_attribute--shown--phrase3

Boundary: http; state: shown

```json
{
  "message": "DHA mein bedrooms kitne hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0abc4269-0fee-42c2-a6d6-508ff327faf0",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "602cdbbf-728c-4abf-ad9b-94f9aad2470c",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0abc4269-0fee-42c2-a6d6-508ff327faf0",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0abc4269-0fee-42c2-a6d6-508ff327faf0",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/bathrooms--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "bathrooms kitne hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "74c4a08d-0362-4eb6-9341-a679cf583c7a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "2",
        "bathrooms",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "d23dc65e-6643-48b1-9033-164990f5d8d8",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "74c4a08d-0362-4eb6-9341-a679cf583c7a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "74c4a08d-0362-4eb6-9341-a679cf583c7a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing '2'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'bathrooms'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/bathrooms--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "bathroom kitne hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ad6d8e3b-25f8-4b07-a9cc-908b5fd96b10",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "2",
        "bathrooms",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "5375a0ed-0f11-4afa-b8e9-feab1aea9bcb",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ad6d8e3b-25f8-4b07-a9cc-908b5fd96b10",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ad6d8e3b-25f8-4b07-a9cc-908b5fd96b10",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing '2'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'bathrooms'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/bathrooms--selected--phrase1

Boundary: http; state: selected

```json
{
  "message": "bathrooms kitne hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4ed16158-785e-451e-9d91-f3984dc5206f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "2",
        "bathrooms"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "c99742ef-0b84-4f36-88cf-d122e6e015b5",
      "message": "Ji, Home P-2 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4ed16158-785e-451e-9d91-f3984dc5206f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4ed16158-785e-451e-9d91-f3984dc5206f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'bathrooms'; actual 'Ji, Home P-2 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.'"
  ]
}
```

## 10_details/bathrooms--selected--phrase2

Boundary: http; state: selected

```json
{
  "message": "bathroom kitne hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "90f20757-d93f-4144-aace-30a6530b59d1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "2",
        "bathrooms"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "49ec2518-ba20-4bd9-905e-0e050058ef4b",
      "message": "Ji, Home P-2 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "90f20757-d93f-4144-aace-30a6530b59d1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "90f20757-d93f-4144-aace-30a6530b59d1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'bathrooms'; actual 'Ji, Home P-2 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.'"
  ]
}
```

## 10_details/bathrooms--single--phrase1

Boundary: http; state: single

```json
{
  "message": "bathrooms kitne hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "101d8193-da09-4ad4-8b7c-1321520ddb6e",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "2",
        "bathrooms"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "ce245c55-bf4b-48b4-94fa-356bdbc61faa",
      "message": "Ji, Home P-1 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "101d8193-da09-4ad4-8b7c-1321520ddb6e",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "101d8193-da09-4ad4-8b7c-1321520ddb6e",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing '2'; actual 'Ji, Home P-1 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.'",
    "response.message: missing 'bathrooms'; actual 'Ji, Home P-1 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.'"
  ]
}
```

## 10_details/bathrooms--single--phrase2

Boundary: http; state: single

```json
{
  "message": "bathroom kitne hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "fd29f766-3455-4d9f-bc99-167e9f20ba44",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "2",
        "bathrooms"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "033652a1-cf93-4f8e-ad84-4978b468c0f3",
      "message": "Ji, Home P-1 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "fd29f766-3455-4d9f-bc99-167e9f20ba44",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "fd29f766-3455-4d9f-bc99-167e9f20ba44",
      "property_order": [
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing '2'; actual 'Ji, Home P-1 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.'",
    "response.message: missing 'bathrooms'; actual 'Ji, Home P-1 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.'"
  ]
}
```

## 10_details/bedrooms--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "bedrooms kitne hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "08aa9d6d-3d3d-4122-8296-5a9dc1db5147",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "3",
        "bedrooms",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "678ab95a-efe0-4280-adef-6d566f4c8712",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "08aa9d6d-3d3d-4122-8296-5a9dc1db5147",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "08aa9d6d-3d3d-4122-8296-5a9dc1db5147",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing '3'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'bedrooms'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/bedrooms--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "rooms kitne hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "223782fd-d3df-4187-a1e7-3d399bb95aa2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "3",
        "bedrooms",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "374f0607-9fcb-4029-91ad-05d4dc4c44bd",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "223782fd-d3df-4187-a1e7-3d399bb95aa2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "223782fd-d3df-4187-a1e7-3d399bb95aa2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing '3'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'bedrooms'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/developer--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "developer kaun hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ba76cb3e-fa5d-4d59-ad45-8d9e4a59147e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "developer",
        "record",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "f86dd8e8-a247-45ca-b777-410aff90970a",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ba76cb3e-fa5d-4d59-ad45-8d9e4a59147e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ba76cb3e-fa5d-4d59-ad45-8d9e4a59147e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'developer'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'record'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/developer--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "builder kon hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "304f9716-0862-44ed-a2f8-e7a26a838444",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "developer",
        "record",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "cde45361-2577-4d72-956d-4a5c7480f151",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "304f9716-0862-44ed-a2f8-e7a26a838444",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "304f9716-0862-44ed-a2f8-e7a26a838444",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'developer'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'record'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/location--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "location kahan hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "68f0c0c9-d61e-49a4-ad6e-c125ab58df92",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Lahore",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "e41112ef-b9d6-4f78-9698-f30d058cdba2",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "68f0c0c9-d61e-49a4-ad6e-c125ab58df92",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "68f0c0c9-d61e-49a4-ad6e-c125ab58df92",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Lahore'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/location--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "location kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b60460c6-23c0-4192-8eb2-c153a82b5141",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Lahore",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "26a1464d-126e-471f-8cf7-419cd669b958",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b60460c6-23c0-4192-8eb2-c153a82b5141",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b60460c6-23c0-4192-8eb2-c153a82b5141",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Lahore'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/multiple--selected--phrase1

Boundary: http; state: selected

```json
{
  "message": "price kya hai aur bathrooms kitne hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e398a989-225e-41db-980f-e0b23a30f0d7",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "bathrooms",
        "price"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "ed1d64aa-cf76-4aa9-a793-d557ae97d38b",
      "message": "Ji, Home P-2 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e398a989-225e-41db-980f-e0b23a30f0d7",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e398a989-225e-41db-980f-e0b23a30f0d7",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'bathrooms'; actual 'Ji, Home P-2 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.'",
    "response.message: missing 'price'; actual 'Ji, Home P-2 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.'"
  ]
}
```

## 10_details/multiple--selected--phrase2

Boundary: http; state: selected

```json
{
  "message": "developer kaun hai aur amenities kya hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "cd0edb7d-ee4e-4306-bb6e-75b448a54006",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "developer",
        "Parking"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "b7ab4a14-b534-4d9c-a105-4b53599744e7",
      "message": "Ji, Home P-2 ka developer record mein nahi mila. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "cd0edb7d-ee4e-4306-bb6e-75b448a54006",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "cd0edb7d-ee4e-4306-bb6e-75b448a54006",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Parking'; actual 'Ji, Home P-2 ka developer record mein nahi mila. Mazeed details ya visit schedule karne ke liye batayein.'"
  ]
}
```

## 10_details/price--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "price kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "01d57c6a-2db6-4f78-893b-a7868f5dd93b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "price",
        "PKR",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "9f428541-b683-4a49-8f79-443a4fcba468",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "01d57c6a-2db6-4f78-893b-a7868f5dd93b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "01d57c6a-2db6-4f78-893b-a7868f5dd93b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'price'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'PKR'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/price--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "keemat kitni hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "d848c4cc-51e2-4375-bab0-a57ad5276d1c",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "price",
        "PKR",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "6b639a7e-4bbb-4c4f-95da-3937885b2ad6",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "d848c4cc-51e2-4375-bab0-a57ad5276d1c",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "d848c4cc-51e2-4375-bab0-a57ad5276d1c",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'price'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'PKR'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/purpose--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "purpose kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "de353003-f824-412b-8ef2-b8eb067df89b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "purchase",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "a07ec036-b60b-4955-b859-e0e1c7f12432",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "de353003-f824-412b-8ef2-b8eb067df89b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "de353003-f824-412b-8ef2-b8eb067df89b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'purchase'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/purpose--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "rent hai ya buy",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "36f316f0-4bbf-4746-8bc2-0ca81fbf571b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "purchase",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "eb2024ed-6ed8-4533-af16-65cbb1d7f3c6",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "36f316f0-4bbf-4746-8bc2-0ca81fbf571b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "36f316f0-4bbf-4746-8bc2-0ca81fbf571b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'purchase'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/size--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "size kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e6a2de0e-1218-4310-a676-10f431ea825e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Home",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "b647434d-e264-420d-9b27-884670998e46",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e6a2de0e-1218-4310-a676-10f431ea825e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e6a2de0e-1218-4310-a676-10f431ea825e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Home'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/size--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "covered area kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e7bfa7da-9f2e-4d65-aae5-b787616f2192",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Home",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "07cb1774-f407-4780-9d8c-021f1acd44ef",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e7bfa7da-9f2e-4d65-aae5-b787616f2192",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e7bfa7da-9f2e-4d65-aae5-b787616f2192",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Home'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/status--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "status kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "6f774063-cec3-4e84-a5e0-4996942d05d6",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Ready",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "759cc781-1f92-497d-9d50-bb725ac8332a",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "6f774063-cec3-4e84-a5e0-4996942d05d6",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "6f774063-cec3-4e84-a5e0-4996942d05d6",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Ready'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/status--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "condition kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b4f88d13-10b0-4060-ac08-d61c54447b28",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "Ready",
        "Home P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "52afe1e1-a697-4568-b782-9d00adbb5f71",
      "message": "Kis option ki baat kar rahe hain? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b4f88d13-10b0-4060-ac08-d61c54447b28",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b4f88d13-10b0-4060-ac08-d61c54447b28",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'Ready'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'",
    "response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'"
  ]
}
```

## 10_details/unavailable--unavailable--phrase1

Boundary: http; state: unavailable

```json
{
  "message": "price kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b338dfae-8e8a-4681-8092-58625bf3f987",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200
    },
    "contains": {
      "response.message": [
        "available nahi"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "6f459675-71d2-4895-900c-a8fcae4e60e0",
      "message": "Kis option ki details chahiye? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b338dfae-8e8a-4681-8092-58625bf3f987",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b338dfae-8e8a-4681-8092-58625bf3f987",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'available nahi'; actual 'Kis option ki details chahiye? Option number bata dein.'"
  ]
}
```

## 10_details/unavailable--unavailable--phrase2

Boundary: http; state: unavailable

```json
{
  "message": "amenities kya hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9a0ce2e7-71a8-4847-8a96-4ad9fdd9960f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200
    },
    "contains": {
      "response.message": [
        "available nahi"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "58f2432a-4cdf-4113-8713-eb00fd13d3fb",
      "message": "Kis option ki details chahiye? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9a0ce2e7-71a8-4847-8a96-4ad9fdd9960f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9a0ce2e7-71a8-4847-8a96-4ad9fdd9960f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'available nahi'; actual 'Kis option ki details chahiye? Option number bata dein.'"
  ]
}
```

## 10_details/unavailable--unavailable--phrase3

Boundary: http; state: unavailable

```json
{
  "message": "details bata dein",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4a39bf36-d539-48f0-9190-6e7b06f621f6",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details"
    }
  },
  "expected": {
    "eq": {
      "status": 200
    },
    "contains": {
      "response.message": [
        "available nahi"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "7d686fbc-1624-43ba-9474-96dec679cde7",
      "message": "Kis option ki details chahiye? Option number bata dein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4a39bf36-d539-48f0-9190-6e7b06f621f6",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4a39bf36-d539-48f0-9190-6e7b06f621f6",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'available nahi'; actual 'Kis option ki details chahiye? Option number bata dein.'"
  ]
}
```

## 11_off_topic/redirect--scope--phrase1

Boundary: http; state: scope

```json
{
  "message": "Pakistan ka capital kya hai",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "84308e76-c09d-44f8-b039-a21cead3d2df",
      "message": "Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "pending_scope_confirm": {
        "city": "Lahore"
      },
      "recent_turns": [
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'"
  ]
}
```

## 11_off_topic/redirect--scope--phrase2

Boundary: http; state: scope

```json
{
  "message": "Python mein loop kaise likhte hain",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "436eaab2-ec79-4629-9b63-b4d5c83be95f",
      "message": "Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "pending_scope_confirm": {
        "city": "Lahore"
      },
      "recent_turns": [
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'"
  ]
}
```

## 11_off_topic/redirect--scope--phrase3

Boundary: http; state: scope

```json
{
  "message": "car khareedni hai",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "ee30aa6d-fd19-4a24-ac6c-698755e903c9",
      "message": "Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "pending_scope_confirm": {
        "city": "Lahore"
      },
      "recent_turns": [
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'"
  ]
}
```

## 11_off_topic/redirect--scope--phrase4

Boundary: http; state: scope

```json
{
  "message": "job dhoond do",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "a966efa3-2d65-4178-bbe4-37eae13b4bcb",
      "message": "Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "pending_scope_confirm": {
        "city": "Lahore"
      },
      "recent_turns": [
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'"
  ]
}
```

## 11_off_topic/redirect--scope--phrase5

Boundary: http; state: scope

```json
{
  "message": "are you human",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "01133723-c5ae-41f3-baf6-f7fc5bb4f516",
      "message": "Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "pending_scope_confirm": {
        "city": "Lahore"
      },
      "recent_turns": [
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'"
  ]
}
```

## 11_off_topic/redirect--scope--phrase6

Boundary: http; state: scope

```json
{
  "message": "tumhara naam kya hai",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "4d4283ef-f132-4b10-86ba-0c1fdbb92593",
      "message": "Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "pending_scope_confirm": {
        "city": "Lahore"
      },
      "recent_turns": [
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'"
  ]
}
```

## 11_off_topic/redirect--scope--phrase7

Boundary: http; state: scope

```json
{
  "message": "yeh test message hai",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "d24ec227-2c25-4dcf-bef3-2c8ef5a5aacf",
      "message": "Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "pending_scope_confirm": {
        "city": "Lahore"
      },
      "recent_turns": [
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'"
  ]
}
```

## 11_off_topic/redirect--scope--phrase8

Boundary: http; state: scope

```json
{
  "message": "recipe bata do",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "eee0728d-14dd-4c36-8760-149c874c5924",
      "message": "Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "pending_scope_confirm": {
        "city": "Lahore"
      },
      "recent_turns": [
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 1,
      "pending_scope_confirm": {
        "city": "Lahore"
      }
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'"
  ]
}
```

## 11_off_topic/redirect--shown--phrase1

Boundary: http; state: shown

```json
{
  "message": "Pakistan ka capital kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "c90b288e-8f18-4863-b875-9e83512b341d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "32fd2edb-d145-4516-93b0-b0562d43a15e",
      "message": "Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "c90b288e-8f18-4863-b875-9e83512b341d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "c90b288e-8f18-4863-b875-9e83512b341d",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?'"
  ]
}
```

## 11_off_topic/redirect--shown--phrase2

Boundary: http; state: shown

```json
{
  "message": "Python mein loop kaise likhte hain",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "8bccbfb9-e944-4c8f-ac3b-a08c507d48d1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "f21dc6d5-6044-4bb1-84b1-65e8ec4d7328",
      "message": "Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "8bccbfb9-e944-4c8f-ac3b-a08c507d48d1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "8bccbfb9-e944-4c8f-ac3b-a08c507d48d1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?'"
  ]
}
```

## 11_off_topic/redirect--shown--phrase3

Boundary: http; state: shown

```json
{
  "message": "car khareedni hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "c25b141d-a9b9-48a5-99d2-542f2c78fcf2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "f01acedc-ddd2-4560-b203-5ce58ab378d5",
      "message": "Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "c25b141d-a9b9-48a5-99d2-542f2c78fcf2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "c25b141d-a9b9-48a5-99d2-542f2c78fcf2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?'"
  ]
}
```

## 11_off_topic/redirect--shown--phrase4

Boundary: http; state: shown

```json
{
  "message": "job dhoond do",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "105a6276-ddfa-4ac8-9283-2f9042dd4161",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "4b5c863b-931d-4450-a237-a449f007b838",
      "message": "Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "105a6276-ddfa-4ac8-9283-2f9042dd4161",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "105a6276-ddfa-4ac8-9283-2f9042dd4161",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?'"
  ]
}
```

## 11_off_topic/redirect--shown--phrase5

Boundary: http; state: shown

```json
{
  "message": "are you human",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "29773ae5-06b5-4e23-90ec-799b4941599e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "7a2932ad-a6d3-464f-8e8c-2a7adaded1f3",
      "message": "Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "29773ae5-06b5-4e23-90ec-799b4941599e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "29773ae5-06b5-4e23-90ec-799b4941599e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?'"
  ]
}
```

## 11_off_topic/redirect--shown--phrase6

Boundary: http; state: shown

```json
{
  "message": "tumhara naam kya hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "5a9066f0-b190-41f3-b811-14e145dbfb0b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "432f5ca6-eeb3-4aeb-9d42-4b139bd52dbf",
      "message": "Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "5a9066f0-b190-41f3-b811-14e145dbfb0b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "5a9066f0-b190-41f3-b811-14e145dbfb0b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?'"
  ]
}
```

## 11_off_topic/redirect--shown--phrase7

Boundary: http; state: shown

```json
{
  "message": "yeh test message hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b896a09c-ac5d-4055-8417-2c7c1cce8613",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "abd0edf6-99c2-4e59-8b49-c7e87c096cca",
      "message": "Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b896a09c-ac5d-4055-8417-2c7c1cce8613",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b896a09c-ac5d-4055-8417-2c7c1cce8613",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?'"
  ]
}
```

## 11_off_topic/redirect--shown--phrase8

Boundary: http; state: shown

```json
{
  "message": "recipe bata do",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "dabf3a00-d016-4bab-ab64-3e867278f0c4",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "off_topic"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ],
    "preserve_prefs": true
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "682826bc-0211-4251-827f-a402245d416b",
      "message": "Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "dabf3a00-d016-4bab-ab64-3e867278f0c4",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "off_topic",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "dabf3a00-d016-4bab-ab64-3e867278f0c4",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Hum abhi DHA (Lahore) ke options dekh rahe hain. Aapke saamne 2 verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?'"
  ]
}
```

## 12_unclear/ambiguous_property_type--mid_returning--phrase1

Boundary: http; state: mid_returning

```json
{
  "message": "apartment ya house",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "25d22fc5-c881-4262-8e77-ca86d33c0f24",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_property_type"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "type"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "fa3bd592-148f-432e-a002-18b27c3d4594",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "25d22fc5-c881-4262-8e77-ca86d33c0f24",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "25d22fc5-c881-4262-8e77-ca86d33c0f24",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'type'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_property_type--mid_returning--phrase2

Boundary: http; state: mid_returning

```json
{
  "message": "flat or house",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "eabed974-94a5-4c50-a451-83344b78a220",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_property_type"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "type"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "b3165287-d920-4359-8d8a-5c16ed042bc5",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "eabed974-94a5-4c50-a451-83344b78a220",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "eabed974-94a5-4c50-a451-83344b78a220",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'type'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_property_type--mid_returning--phrase3

Boundary: http; state: mid_returning

```json
{
  "message": "house ya apartment",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "d0fd3692-3448-40b2-8005-9cedc1351a16",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_property_type"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "type"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "2f248d1a-b401-48a4-8329-10f8ffa4d2ea",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "d0fd3692-3448-40b2-8005-9cedc1351a16",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "d0fd3692-3448-40b2-8005-9cedc1351a16",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'type'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_property_type--shown--phrase1

Boundary: http; state: shown

```json
{
  "message": "apartment ya house",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "6cbef159-fa86-4ed7-9938-a8c440d81763",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_property_type"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "type"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "98a4c0e6-b816-4e5d-9349-741f2d4ecbd4",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "6cbef159-fa86-4ed7-9938-a8c440d81763",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "6cbef159-fa86-4ed7-9938-a8c440d81763",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'type'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_property_type--shown--phrase2

Boundary: http; state: shown

```json
{
  "message": "flat or house",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e6b8f862-22a6-4174-a200-21a8e5f73c7a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_property_type"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "type"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "3733b91d-d204-4231-a089-3e777ef9ed42",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e6b8f862-22a6-4174-a200-21a8e5f73c7a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "e6b8f862-22a6-4174-a200-21a8e5f73c7a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'type'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_property_type--shown--phrase3

Boundary: http; state: shown

```json
{
  "message": "house ya apartment",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "5f99cec0-428b-4383-b742-7356c375a229",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_property_type"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "type"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "c66536d2-3523-44a5-8d68-44d7cbc6c6cd",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "5f99cec0-428b-4383-b742-7356c375a229",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "5f99cec0-428b-4383-b742-7356c375a229",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'type'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_purpose--mid_returning--phrase1

Boundary: http; state: mid_returning

```json
{
  "message": "rent ya buy",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "7d8d077b-ce3a-4b66-ac4b-81154961ce2e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_purpose"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "rent"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "862cd0b8-fad7-4bd1-98db-a914926f65e1",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "7d8d077b-ce3a-4b66-ac4b-81154961ce2e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "7d8d077b-ce3a-4b66-ac4b-81154961ce2e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'rent'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_purpose--mid_returning--phrase2

Boundary: http; state: mid_returning

```json
{
  "message": "purchase aur rental dono",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "7abc4d8f-e16c-41ad-a346-86b866f0432e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_purpose"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "rent"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "b790daa8-d52f-4da5-b38d-b758bb529ae5",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "7abc4d8f-e16c-41ad-a346-86b866f0432e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "7abc4d8f-e16c-41ad-a346-86b866f0432e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'rent'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_purpose--mid_returning--phrase3

Boundary: http; state: mid_returning

```json
{
  "message": "khareedna hai ya rent lena hai",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0b4a8971-05a7-4c89-b842-e4d189876815",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_purpose"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "rent"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "13810db0-55d0-40bb-ba25-085e35772ce7",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0b4a8971-05a7-4c89-b842-e4d189876815",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0b4a8971-05a7-4c89-b842-e4d189876815",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'rent'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_purpose--shown--phrase1

Boundary: http; state: shown

```json
{
  "message": "rent ya buy",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b2890545-001f-4830-a9b1-9c5650c37a71",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_purpose"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "rent"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "7d46bcc7-9f0f-4b9f-b746-73fd2d6ece28",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b2890545-001f-4830-a9b1-9c5650c37a71",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b2890545-001f-4830-a9b1-9c5650c37a71",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'rent'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_purpose--shown--phrase2

Boundary: http; state: shown

```json
{
  "message": "purchase aur rental dono",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "8237f482-68b5-446d-a0f3-b17d2ee11f1c",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_purpose"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "rent"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "59109c03-a073-4579-8ec1-0317b7b0fae2",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "8237f482-68b5-446d-a0f3-b17d2ee11f1c",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "8237f482-68b5-446d-a0f3-b17d2ee11f1c",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'rent'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 12_unclear/ambiguous_purpose--shown--phrase3

Boundary: http; state: shown

```json
{
  "message": "khareedna hai ya rent lena hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "14c0dd13-66a8-43b8-8b05-382c6f974404",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "needs_clarification": true,
      "clarification_reason": "ambiguous_purpose"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "rent"
      ]
    },
    "empty": [
      "response.properties",
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "4b962ff0-f459-4a03-9576-799f573311c3",
      "message": "Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "14c0dd13-66a8-43b8-8b05-382c6f974404",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "14c0dd13-66a8-43b8-8b05-382c6f974404",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'rent'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'"
  ]
}
```

## 13_multi_intent/details_booking--mid_returning--phrase1

Boundary: http; state: mid_returning

```json
{
  "message": "price kya hai aur pehli ki visit book kar dein",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "2cad372d-c940-47ed-8528-9490da80d48a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "truthy": [
      "saved.pending_action"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "a9dd49b6-5ff7-499f-98a2-7a91729b21ce",
      "message": "Ji, Home P-2 ki price 1.20 Crore PKR hai. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "2cad372d-c940-47ed-8528-9490da80d48a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "2cad372d-c940-47ed-8528-9490da80d48a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'date'; actual 'Ji, Home P-2 ki price 1.20 Crore PKR hai. Mazeed details ya visit schedule karne ke liye batayein.'",
    "response.message: missing 'time'; actual 'Ji, Home P-2 ki price 1.20 Crore PKR hai. Mazeed details ya visit schedule karne ke liye batayein.'",
    "saved.pending_action: expected nonempty, actual None"
  ]
}
```

## 13_multi_intent/details_booking--mid_returning--phrase2

Boundary: http; state: mid_returning

```json
{
  "message": "amenities kya hain, first ki visit bhi karni hai",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "36560a8a-7cd1-4a06-8f7e-68df13d81fd2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "truthy": [
      "saved.pending_action"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "68e43fba-7a67-4591-82d5-4fd7ff20229f",
      "message": "Ji, Home P-2 ki amenities hain: Parking. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "36560a8a-7cd1-4a06-8f7e-68df13d81fd2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "36560a8a-7cd1-4a06-8f7e-68df13d81fd2",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'date'; actual 'Ji, Home P-2 ki amenities hain: Parking. Mazeed details ya visit schedule karne ke liye batayein.'",
    "response.message: missing 'time'; actual 'Ji, Home P-2 ki amenities hain: Parking. Mazeed details ya visit schedule karne ke liye batayein.'",
    "saved.pending_action: expected nonempty, actual None"
  ]
}
```

## 13_multi_intent/details_booking--mid_returning--phrase3

Boundary: http; state: mid_returning

```json
{
  "message": "location kahan hai aur option 1 visit schedule kar dein",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "12aac74e-1cba-4af1-a6d1-574e26172592",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "truthy": [
      "saved.pending_action"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "83cdc6e8-e7d8-47e4-b039-84e012527e3f",
      "message": "Ji, Home P-2 DHA, Lahore mein hai. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "12aac74e-1cba-4af1-a6d1-574e26172592",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "12aac74e-1cba-4af1-a6d1-574e26172592",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'date'; actual 'Ji, Home P-2 DHA, Lahore mein hai. Mazeed details ya visit schedule karne ke liye batayein.'",
    "response.message: missing 'time'; actual 'Ji, Home P-2 DHA, Lahore mein hai. Mazeed details ya visit schedule karne ke liye batayein.'",
    "saved.pending_action: expected nonempty, actual None"
  ]
}
```

## 13_multi_intent/details_booking--shown--phrase1

Boundary: http; state: shown

```json
{
  "message": "price kya hai aur pehli ki visit book kar dein",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "f1276198-09e3-49d5-9971-907ecac582a0",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "truthy": [
      "saved.pending_action"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "622207ce-e619-4d6f-9d54-95675c5b5463",
      "message": "Ji, Home P-2 ki price 1.20 Crore PKR hai. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "f1276198-09e3-49d5-9971-907ecac582a0",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "f1276198-09e3-49d5-9971-907ecac582a0",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'date'; actual 'Ji, Home P-2 ki price 1.20 Crore PKR hai. Mazeed details ya visit schedule karne ke liye batayein.'",
    "response.message: missing 'time'; actual 'Ji, Home P-2 ki price 1.20 Crore PKR hai. Mazeed details ya visit schedule karne ke liye batayein.'",
    "saved.pending_action: expected nonempty, actual None"
  ]
}
```

## 13_multi_intent/details_booking--shown--phrase2

Boundary: http; state: shown

```json
{
  "message": "amenities kya hain, first ki visit bhi karni hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "338ac93f-0227-465e-94c0-a2fdfc500a3a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "truthy": [
      "saved.pending_action"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "74c002eb-d1b9-4f1c-99a4-b887232eea16",
      "message": "Ji, Home P-2 ki amenities hain: Parking. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "338ac93f-0227-465e-94c0-a2fdfc500a3a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "338ac93f-0227-465e-94c0-a2fdfc500a3a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'date'; actual 'Ji, Home P-2 ki amenities hain: Parking. Mazeed details ya visit schedule karne ke liye batayein.'",
    "response.message: missing 'time'; actual 'Ji, Home P-2 ki amenities hain: Parking. Mazeed details ya visit schedule karne ke liye batayein.'",
    "saved.pending_action: expected nonempty, actual None"
  ]
}
```

## 13_multi_intent/details_booking--shown--phrase3

Boundary: http; state: shown

```json
{
  "message": "location kahan hai aur option 1 visit schedule kar dein",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "5c306d37-fb80-4a8c-8e33-7b7185e33fa1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "date",
        "time"
      ]
    },
    "truthy": [
      "saved.pending_action"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "b0e8f2c8-b91d-4305-aff5-d7fef2c1feb4",
      "message": "Ji, Home P-2 DHA, Lahore mein hai. Mazeed details ya visit schedule karne ke liye batayein.",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "5c306d37-fb80-4a8c-8e33-7b7185e33fa1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "5c306d37-fb80-4a8c-8e33-7b7185e33fa1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'date'; actual 'Ji, Home P-2 DHA, Lahore mein hai. Mazeed details ya visit schedule karne ke liye batayein.'",
    "response.message: missing 'time'; actual 'Ji, Home P-2 DHA, Lahore mein hai. Mazeed details ya visit schedule karne ke liye batayein.'",
    "saved.pending_action: expected nonempty, actual None"
  ]
}
```

## 13_multi_intent/feedback_criteria--mid_returning--phrase1

Boundary: http; state: mid_returning

```json
{
  "message": "pehli pasand hai lekin ab budget 3 crore",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0dd562c2-c7e6-485b-af1e-8ad278969598",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "interaction_action": "liked",
      "selected_index": 0,
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "prefs.budget_max": 30000000
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "1348ce57-bba8-418f-9529-aaae45d49eca",
      "message": "Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 30000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "0dd562c2-c7e6-485b-af1e-8ad278969598",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected nonempty, actual []"
  ]
}
```

## 13_multi_intent/feedback_criteria--mid_returning--phrase2

Boundary: http; state: mid_returning

```json
{
  "message": "like first, budget ab 3 crore",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "158f0809-308c-4e4a-a56e-c980eed6c820",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "interaction_action": "liked",
      "selected_index": 0,
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "prefs.budget_max": 30000000
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "c571ed9a-32ab-4d5f-8b6f-f3db0aaf3012",
      "message": "Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 30000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "158f0809-308c-4e4a-a56e-c980eed6c820",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected nonempty, actual []"
  ]
}
```

## 13_multi_intent/feedback_criteria--mid_returning--phrase3

Boundary: http; state: mid_returning

```json
{
  "message": "first option achi hai, budget increase to 3 crore",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "56e650c0-fd66-48bf-9021-ebab140b254f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "interaction_action": "liked",
      "selected_index": 0,
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "prefs.budget_max": 30000000
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "bb96eb43-b9ed-4591-9dc7-c132c3bba915",
      "message": "Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 3,
      "flexible": [],
      "excluded": {},
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 30000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "pending_returning_confirm": false,
      "returning_customer_handled": true,
      "turn_count": 2,
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "56e650c0-fd66-48bf-9021-ebab140b254f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected nonempty, actual []"
  ]
}
```

## 13_multi_intent/feedback_criteria--shown--phrase1

Boundary: http; state: shown

```json
{
  "message": "pehli pasand hai lekin ab budget 3 crore",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "dd39c1e7-f92c-45ec-a27a-0258770fa983",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "interaction_action": "liked",
      "selected_index": 0,
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "prefs.budget_max": 30000000
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "ed76c760-fe9a-42ad-b0c2-fbf51e392be5",
      "message": "Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 30000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "dd39c1e7-f92c-45ec-a27a-0258770fa983",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected nonempty, actual []"
  ]
}
```

## 13_multi_intent/feedback_criteria--shown--phrase2

Boundary: http; state: shown

```json
{
  "message": "like first, budget ab 3 crore",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "60b37303-97d5-4606-a9ab-58f3fef878a3",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "interaction_action": "liked",
      "selected_index": 0,
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "prefs.budget_max": 30000000
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "943eb426-2860-4fad-9896-c0d09f77f52f",
      "message": "Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 30000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "60b37303-97d5-4606-a9ab-58f3fef878a3",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected nonempty, actual []"
  ]
}
```

## 13_multi_intent/feedback_criteria--shown--phrase3

Boundary: http; state: shown

```json
{
  "message": "first option achi hai, budget increase to 3 crore",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "a3033c55-3b52-46d2-95b6-2194ecb2cb47",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "interaction_action": "liked",
      "selected_index": 0,
      "required": {
        "budget": 30000000
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "prefs.budget_max": 30000000
    },
    "truthy": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "99c5830b-7667-46cb-9e25-7808742926c6",
      "message": "Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_search",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 30000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "a3033c55-3b52-46d2-95b6-2194ecb2cb47",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected nonempty, actual []"
  ]
}
```

## 14_language/urdu_script--known--phrase1

Boundary: deterministic; state: known

```json
{
  "message": "مجھے مکان چاہیے",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "exception": "UnderstandingError",
      "error": "unsupported_script"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "مجھے مکان چاہیے",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 15,
    "provider_calls": 1
  },
  "violations": [
    "exception: expected 'UnderstandingError', actual None",
    "error: expected 'unsupported_script', actual None"
  ]
}
```

## 14_language/urdu_script--known--phrase2

Boundary: deterministic; state: known

```json
{
  "message": "لاہور میں گھر دکھائیں",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "exception": "UnderstandingError",
      "error": "unsupported_script"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "لاہور میں گھر دکھائیں",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 21,
    "provider_calls": 1
  },
  "violations": [
    "exception: expected 'UnderstandingError', actual None",
    "error: expected 'unsupported_script', actual None"
  ]
}
```

## 14_language/urdu_script--known--phrase3

Boundary: deterministic; state: known

```json
{
  "message": "بجٹ تین کروڑ ہے",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "exception": "UnderstandingError",
      "error": "unsupported_script"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "بجٹ تین کروڑ ہے",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 15,
    "provider_calls": 1
  },
  "violations": [
    "exception: expected 'UnderstandingError', actual None",
    "error: expected 'unsupported_script', actual None"
  ]
}
```

## 14_language/urdu_script--mid_returning--phrase1

Boundary: deterministic; state: mid_returning

```json
{
  "message": "مجھے مکان چاہیے",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "exception": "UnderstandingError",
      "error": "unsupported_script"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "مجھے مکان چاہیے",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 15,
    "provider_calls": 1
  },
  "violations": [
    "exception: expected 'UnderstandingError', actual None",
    "error: expected 'unsupported_script', actual None"
  ]
}
```

## 14_language/urdu_script--mid_returning--phrase2

Boundary: deterministic; state: mid_returning

```json
{
  "message": "لاہور میں گھر دکھائیں",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "exception": "UnderstandingError",
      "error": "unsupported_script"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "لاہور میں گھر دکھائیں",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 21,
    "provider_calls": 1
  },
  "violations": [
    "exception: expected 'UnderstandingError', actual None",
    "error: expected 'unsupported_script', actual None"
  ]
}
```

## 14_language/urdu_script--mid_returning--phrase3

Boundary: deterministic; state: mid_returning

```json
{
  "message": "بجٹ تین کروڑ ہے",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "exception": "UnderstandingError",
      "error": "unsupported_script"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "بجٹ تین کروڑ ہے",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 15,
    "provider_calls": 1
  },
  "violations": [
    "exception: expected 'UnderstandingError', actual None",
    "error: expected 'unsupported_script', actual None"
  ]
}
```

## 14_language/urdu_script--new--phrase1

Boundary: deterministic; state: new

```json
{
  "message": "مجھے مکان چاہیے",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "exception": "UnderstandingError",
      "error": "unsupported_script"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "مجھے مکان چاہیے",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 15,
    "provider_calls": 1
  },
  "violations": [
    "exception: expected 'UnderstandingError', actual None",
    "error: expected 'unsupported_script', actual None"
  ]
}
```

## 14_language/urdu_script--new--phrase2

Boundary: deterministic; state: new

```json
{
  "message": "لاہور میں گھر دکھائیں",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "exception": "UnderstandingError",
      "error": "unsupported_script"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "لاہور میں گھر دکھائیں",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 21,
    "provider_calls": 1
  },
  "violations": [
    "exception: expected 'UnderstandingError', actual None",
    "error: expected 'unsupported_script', actual None"
  ]
}
```

## 14_language/urdu_script--new--phrase3

Boundary: deterministic; state: new

```json
{
  "message": "بجٹ تین کروڑ ہے",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": true
  },
  "expected": {
    "eq": {
      "exception": "UnderstandingError",
      "error": "unsupported_script"
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "بجٹ تین کروڑ ہے",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 15,
    "provider_calls": 1
  },
  "violations": [
    "exception: expected 'UnderstandingError', actual None",
    "error: expected 'unsupported_script', actual None"
  ]
}
```

## 16_session_context/booking--stale--phrase1

Boundary: http; state: stale

```json
{
  "message": "pehli ki visit book kar dein",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0,
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "empty": [
      "appointments",
      "event_ids"
    ]
  },
  "actual": {
    "status": 503,
    "response": {
      "detail": "Sara chat is temporarily unavailable. Please try again."
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "status: expected 200, actual 503",
    "response.requires_clarification: expected True, actual None"
  ]
}
```

## 16_session_context/booking--stale--phrase2

Boundary: http; state: stale

```json
{
  "message": "first option visit please",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0,
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "empty": [
      "appointments",
      "event_ids"
    ]
  },
  "actual": {
    "status": 503,
    "response": {
      "detail": "Sara chat is temporarily unavailable. Please try again."
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "status: expected 200, actual 503",
    "response.requires_clarification: expected True, actual None"
  ]
}
```

## 16_session_context/details--stale--phrase1

Boundary: http; state: stale

```json
{
  "message": "pehli ki details",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "empty": [
      "appointments",
      "event_ids"
    ]
  },
  "actual": {
    "status": 503,
    "response": {
      "detail": "Sara chat is temporarily unavailable. Please try again."
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "status: expected 200, actual 503",
    "response.requires_clarification: expected True, actual None"
  ]
}
```

## 16_session_context/details--stale--phrase2

Boundary: http; state: stale

```json
{
  "message": "first option details please",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_details",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "empty": [
      "appointments",
      "event_ids"
    ]
  },
  "actual": {
    "status": 503,
    "response": {
      "detail": "Sara chat is temporarily unavailable. Please try again."
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "status: expected 200, actual 503",
    "response.requires_clarification: expected True, actual None"
  ]
}
```

## 17_negation/amenity--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "gym nahi chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.amenities": [
        "Gym"
      ]
    },
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "gym nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "excluded.amenities: missing 'Gym'; actual None",
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 17_negation/amenity--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "no gym",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.amenities": [
        "Gym"
      ]
    },
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no gym",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 6,
    "provider_calls": 1
  },
  "violations": [
    "excluded.amenities: missing 'Gym'; actual None",
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 17_negation/amenity--mid_returning--phrase3

Boundary: repair; state: mid_returning

```json
{
  "message": "gym ke baghair",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.amenities": [
        "Gym"
      ]
    },
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "gym ke baghair",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 14,
    "provider_calls": 1
  },
  "violations": [
    "excluded.amenities: missing 'Gym'; actual None",
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 17_negation/amenity--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "gym nahi chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.amenities": [
        "Gym"
      ]
    },
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "gym nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "excluded.amenities: missing 'Gym'; actual None",
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 17_negation/amenity--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "no gym",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.amenities": [
        "Gym"
      ]
    },
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no gym",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 6,
    "provider_calls": 1
  },
  "violations": [
    "excluded.amenities: missing 'Gym'; actual None",
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 17_negation/amenity--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "gym ke baghair",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.amenities": [
        "Gym"
      ]
    },
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "gym ke baghair",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 14,
    "provider_calls": 1
  },
  "violations": [
    "excluded.amenities: missing 'Gym'; actual None",
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 17_negation/area--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "DHA nahi chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/area--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "DHA ke ilawa",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA ke ilawa",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/area--mid_returning--phrase3

Boundary: repair; state: mid_returning

```json
{
  "message": "no DHA please",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no DHA please",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 13,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/area--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "DHA nahi chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/area--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "DHA ke ilawa",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA ke ilawa",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 12,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/area--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "no DHA please",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no DHA please",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 13,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/double--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "nahi DHA nahi chahiye ab",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "nahi DHA nahi chahiye ab",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 24,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/double--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "nahi ab DHA nahi",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "nahi ab DHA nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/double--mid_returning--phrase3

Boundary: repair; state: mid_returning

```json
{
  "message": "no, not DHA anymore",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no, not DHA anymore",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 19,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/double--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "nahi DHA nahi chahiye ab",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "nahi DHA nahi chahiye ab",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 24,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/double--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "nahi ab DHA nahi",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "nahi ab DHA nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/double--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "no, not DHA anymore",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no, not DHA anymore",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 19,
    "provider_calls": 1
  },
  "violations": [
    "excluded.area: missing 'DHA'; actual None",
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/preserve_exclusion_amenities--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "gym nahi chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "amenities": [
          "Gym"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.amenities": [
        "Gym"
      ]
    },
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {
      "amenities": [
        "Gym"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "gym nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 17_negation/preserve_exclusion_amenities--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "no gym please",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "amenities": [
          "Gym"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.amenities": [
        "Gym"
      ]
    },
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {
      "amenities": [
        "Gym"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no gym please",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 13,
    "provider_calls": 1
  },
  "violations": [
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 17_negation/preserve_exclusion_amenities--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "gym nahi chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "amenities": [
          "Gym"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.amenities": [
        "Gym"
      ]
    },
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {
      "amenities": [
        "Gym"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "gym nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 17_negation/preserve_exclusion_amenities--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "no gym please",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "amenities": [
          "Gym"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.amenities": [
        "Gym"
      ]
    },
    "excludes": {
      "required.amenities": [
        "Gym"
      ],
      "preferred.amenities": [
        "Gym"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {},
    "preferred": {
      "amenities": [
        "Gym"
      ]
    },
    "excluded": {
      "amenities": [
        "Gym"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no gym please",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 13,
    "provider_calls": 1
  },
  "violations": [
    "preferred.amenities: must not contain 'Gym'; actual ['Gym']"
  ]
}
```

## 17_negation/preserve_exclusion_area--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "DHA nahi chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "area": [
          "DHA"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {
      "area": [
        "DHA"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/preserve_exclusion_area--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "nahi DHA nahi chahiye ab",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "area": [
          "DHA"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {
      "area": [
        "DHA"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "nahi DHA nahi chahiye ab",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 24,
    "provider_calls": 1
  },
  "violations": [
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/preserve_exclusion_area--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "DHA nahi chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "area": [
          "DHA"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {
      "area": [
        "DHA"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "DHA nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 16,
    "provider_calls": 1
  },
  "violations": [
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/preserve_exclusion_area--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "nahi DHA nahi chahiye ab",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "area": [
          "DHA"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.area": [
        "DHA"
      ]
    },
    "excludes": {
      "required.area": [
        "DHA"
      ],
      "preferred.area": [
        "DHA"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "area": "DHA"
    },
    "preferred": {},
    "excluded": {
      "area": [
        "DHA"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "nahi DHA nahi chahiye ab",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 24,
    "provider_calls": 1
  },
  "violations": [
    "required.area: must not contain 'DHA'; actual 'DHA'"
  ]
}
```

## 17_negation/preserve_exclusion_purpose--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "rent nahi chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "purpose": [
          "Rental"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.purpose": [
        "Rental"
      ]
    },
    "excludes": {
      "required.purpose": [
        "Rental"
      ],
      "preferred.purpose": [
        "Rental"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "purpose": "Rental"
    },
    "preferred": {},
    "excluded": {
      "purpose": [
        "Rental"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rent nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "required.purpose: must not contain 'Rental'; actual 'Rental'"
  ]
}
```

## 17_negation/preserve_exclusion_purpose--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "rental nahi",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "purpose": [
          "Rental"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.purpose": [
        "Rental"
      ]
    },
    "excludes": {
      "required.purpose": [
        "Rental"
      ],
      "preferred.purpose": [
        "Rental"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "purpose": "Rental"
    },
    "preferred": {},
    "excluded": {
      "purpose": [
        "Rental"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rental nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.purpose: must not contain 'Rental'; actual 'Rental'"
  ]
}
```

## 17_negation/preserve_exclusion_purpose--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "rent nahi chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "purpose": [
          "Rental"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.purpose": [
        "Rental"
      ]
    },
    "excludes": {
      "required.purpose": [
        "Rental"
      ],
      "preferred.purpose": [
        "Rental"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "purpose": "Rental"
    },
    "preferred": {},
    "excluded": {
      "purpose": [
        "Rental"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rent nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "required.purpose: must not contain 'Rental'; actual 'Rental'"
  ]
}
```

## 17_negation/preserve_exclusion_purpose--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "rental nahi",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "property_search",
      "excluded": {
        "purpose": [
          "Rental"
        ]
      }
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.purpose": [
        "Rental"
      ]
    },
    "excludes": {
      "required.purpose": [
        "Rental"
      ],
      "preferred.purpose": [
        "Rental"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "purpose": "Rental"
    },
    "preferred": {},
    "excluded": {
      "purpose": [
        "Rental"
      ]
    },
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rental nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "required.purpose: must not contain 'Rental'; actual 'Rental'"
  ]
}
```

## 17_negation/purpose--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "rent nahi chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.purpose": [
        "Rental"
      ]
    },
    "excludes": {
      "required.purpose": [
        "Rental"
      ],
      "preferred.purpose": [
        "Rental"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "purpose": "Rental"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rent nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "excluded.purpose: missing 'Rental'; actual None",
    "required.purpose: must not contain 'Rental'; actual 'Rental'"
  ]
}
```

## 17_negation/purpose--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "rental nahi",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.purpose": [
        "Rental"
      ]
    },
    "excludes": {
      "required.purpose": [
        "Rental"
      ],
      "preferred.purpose": [
        "Rental"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "purpose": "Rental"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rental nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "excluded.purpose: missing 'Rental'; actual None",
    "required.purpose: must not contain 'Rental'; actual 'Rental'"
  ]
}
```

## 17_negation/purpose--mid_returning--phrase3

Boundary: repair; state: mid_returning

```json
{
  "message": "no rent please",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.purpose": [
        "Rental"
      ]
    },
    "excludes": {
      "required.purpose": [
        "Rental"
      ],
      "preferred.purpose": [
        "Rental"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "purpose": "Rental"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no rent please",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 14,
    "provider_calls": 1
  },
  "violations": [
    "excluded.purpose: missing 'Rental'; actual None",
    "required.purpose: must not contain 'Rental'; actual 'Rental'"
  ]
}
```

## 17_negation/purpose--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "rent nahi chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.purpose": [
        "Rental"
      ]
    },
    "excludes": {
      "required.purpose": [
        "Rental"
      ],
      "preferred.purpose": [
        "Rental"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "purpose": "Rental"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rent nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 17,
    "provider_calls": 1
  },
  "violations": [
    "excluded.purpose: missing 'Rental'; actual None",
    "required.purpose: must not contain 'Rental'; actual 'Rental'"
  ]
}
```

## 17_negation/purpose--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "rental nahi",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.purpose": [
        "Rental"
      ]
    },
    "excludes": {
      "required.purpose": [
        "Rental"
      ],
      "preferred.purpose": [
        "Rental"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "purpose": "Rental"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "rental nahi",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 11,
    "provider_calls": 1
  },
  "violations": [
    "excluded.purpose: missing 'Rental'; actual None",
    "required.purpose: must not contain 'Rental'; actual 'Rental'"
  ]
}
```

## 17_negation/purpose--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "no rent please",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.purpose": [
        "Rental"
      ]
    },
    "excludes": {
      "required.purpose": [
        "Rental"
      ],
      "preferred.purpose": [
        "Rental"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "purpose": "Rental"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no rent please",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 14,
    "provider_calls": 1
  },
  "violations": [
    "excluded.purpose: missing 'Rental'; actual None",
    "required.purpose: must not contain 'Rental'; actual 'Rental'"
  ]
}
```

## 17_negation/type--mid_returning--phrase1

Boundary: repair; state: mid_returning

```json
{
  "message": "apartment nahi chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.property_type": [
        "Apartment"
      ]
    },
    "excludes": {
      "required.property_type": [
        "Apartment"
      ],
      "preferred.property_type": [
        "Apartment"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "apartment nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 22,
    "provider_calls": 1
  },
  "violations": [
    "excluded.property_type: missing 'Apartment'; actual None"
  ]
}
```

## 17_negation/type--mid_returning--phrase2

Boundary: repair; state: mid_returning

```json
{
  "message": "flat nahin chahiye",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.property_type": [
        "Apartment"
      ]
    },
    "excludes": {
      "required.property_type": [
        "Apartment"
      ],
      "preferred.property_type": [
        "Apartment"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "flat nahin chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 18,
    "provider_calls": 1
  },
  "violations": [
    "excluded.property_type: missing 'Apartment'; actual None"
  ]
}
```

## 17_negation/type--mid_returning--phrase3

Boundary: repair; state: mid_returning

```json
{
  "message": "no apartment please",
  "effective_context": {
    "context": {
      "required": {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "Purchase",
        "budget": 20000000
      },
      "preferred": {},
      "excluded": {},
      "recent_turns": [
        {
          "intent": "greeting"
        }
      ],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.property_type": [
        "Apartment"
      ]
    },
    "excludes": {
      "required.property_type": [
        "Apartment"
      ],
      "preferred.property_type": [
        "Apartment"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "property_type": "Apartment"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no apartment please",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 19,
    "provider_calls": 1
  },
  "violations": [
    "excluded.property_type: missing 'Apartment'; actual None",
    "required.property_type: must not contain 'Apartment'; actual 'Apartment'"
  ]
}
```

## 17_negation/type--new--phrase1

Boundary: repair; state: new

```json
{
  "message": "apartment nahi chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.property_type": [
        "Apartment"
      ]
    },
    "excludes": {
      "required.property_type": [
        "Apartment"
      ],
      "preferred.property_type": [
        "Apartment"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "apartment nahi chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 22,
    "provider_calls": 1
  },
  "violations": [
    "excluded.property_type: missing 'Apartment'; actual None"
  ]
}
```

## 17_negation/type--new--phrase2

Boundary: repair; state: new

```json
{
  "message": "flat nahin chahiye",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.property_type": [
        "Apartment"
      ]
    },
    "excludes": {
      "required.property_type": [
        "Apartment"
      ],
      "preferred.property_type": [
        "Apartment"
      ]
    }
  },
  "actual": {
    "intent": "unknown",
    "required": {},
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "flat nahin chahiye",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 18,
    "provider_calls": 1
  },
  "violations": [
    "excluded.property_type: missing 'Apartment'; actual None"
  ]
}
```

## 17_negation/type--new--phrase3

Boundary: repair; state: new

```json
{
  "message": "no apartment please",
  "effective_context": {
    "context": {
      "required": {},
      "preferred": {},
      "excluded": {},
      "recent_turns": [],
      "pending_action": null,
      "timezone": "Asia/Karachi",
      "current_date": "2030-01-01T09:00:00+05:00"
    },
    "provider_reply": {
      "intent": "unknown"
    },
    "deterministic_first": false
  },
  "expected": {
    "contains": {
      "excluded.property_type": [
        "Apartment"
      ]
    },
    "excludes": {
      "required.property_type": [
        "Apartment"
      ],
      "preferred.property_type": [
        "Apartment"
      ]
    }
  },
  "actual": {
    "intent": "property_search",
    "required": {
      "property_type": "Apartment"
    },
    "preferred": {},
    "excluded": {},
    "relax": [],
    "reference_type": null,
    "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
    "comparison": {
      "field": null,
      "operator": null,
      "reference": null,
      "value": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "raw_message": "no apartment please",
    "appointment_id": null,
    "starts_at": null,
    "raw_length": 19,
    "provider_calls": 1
  },
  "violations": [
    "excluded.property_type: missing 'Apartment'; actual None",
    "required.property_type: must not contain 'Apartment'; actual 'Apartment'"
  ]
}
```

## 19_references/first_index--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "1",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b1c86bd4-9d2a-415c-a69c-3adbc4a709f5",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "1873a7cd-3fe8-4565-bfc8-3712fe9924f5",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b1c86bd4-9d2a-415c-a69c-3adbc4a709f5",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "b1c86bd4-9d2a-415c-a69c-3adbc4a709f5",
        "property_id": "P-2",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "b1c86bd4-9d2a-415c-a69c-3adbc4a709f5",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 19_references/first_index--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "pehli",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "92cd0b87-b92f-4fa0-95b4-62442bd9ae3b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "095206d6-b1b8-46aa-9906-683b0577fa31",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "92cd0b87-b92f-4fa0-95b4-62442bd9ae3b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "92cd0b87-b92f-4fa0-95b4-62442bd9ae3b",
        "property_id": "P-2",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "92cd0b87-b92f-4fa0-95b4-62442bd9ae3b",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 19_references/first_index--filtered--phrase3

Boundary: http; state: filtered

```json
{
  "message": "first option",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ea746c1c-95de-490a-9652-d72502803e61",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "selected_index": 0
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "55cbeeea-e39b-420a-9a44-5cd53448d088",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ea746c1c-95de-490a-9652-d72502803e61",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "ea746c1c-95de-490a-9652-d72502803e61",
        "property_id": "P-2",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ea746c1c-95de-490a-9652-d72502803e61",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 19_references/first_word--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "pehli wali",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4f0e2a6a-caf3-4ae3-ab51-cd8c67da0fe4",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "reference_type": "first_result"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "e7b53d44-3cb1-48d3-80ea-c987eeaeb65d",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4f0e2a6a-caf3-4ae3-ab51-cd8c67da0fe4",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "4f0e2a6a-caf3-4ae3-ab51-cd8c67da0fe4",
        "property_id": "P-2",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "4f0e2a6a-caf3-4ae3-ab51-cd8c67da0fe4",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 19_references/first_word--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "first result",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ead41943-b2bb-4d76-9997-cdd18a1fc5c7",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "reference_type": "first_result"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "4be46379-724b-490a-bf2c-2c341c23e5dd",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ead41943-b2bb-4d76-9997-cdd18a1fc5c7",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "ead41943-b2bb-4d76-9997-cdd18a1fc5c7",
        "property_id": "P-2",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "ead41943-b2bb-4d76-9997-cdd18a1fc5c7",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 19_references/first_word--filtered--phrase3

Boundary: http; state: filtered

```json
{
  "message": "sab se pehli",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "34386648-a548-4b3a-8344-6a31ee53f096",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "reference_type": "first_result"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "daf23bfe-b197-4fd4-a986-7c8aa968107e",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "34386648-a548-4b3a-8344-6a31ee53f096",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "34386648-a548-4b3a-8344-6a31ee53f096",
        "property_id": "P-2",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "Gulberg",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "34386648-a548-4b3a-8344-6a31ee53f096",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-2"
    ],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 19_references/pronoun--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "yeh wala",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "1e6b74c7-5b72-4efc-9d70-a11b9ca94427",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "reference_type": "selected_property"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "822343c3-1dc5-49aa-9e4a-ed3dfcd21e03",
      "message": "Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "1e6b74c7-5b72-4efc-9d70-a11b9ca94427",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "1e6b74c7-5b72-4efc-9d70-a11b9ca94427",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual []"
  ]
}
```

## 19_references/pronoun--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "is wala",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "87a6d671-9431-492f-8f60-465b65c23256",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "reference_type": "selected_property"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "672e2472-8e46-47d5-8b3e-bc9d96ce512b",
      "message": "Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "87a6d671-9431-492f-8f60-465b65c23256",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "87a6d671-9431-492f-8f60-465b65c23256",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual []"
  ]
}
```

## 19_references/pronoun--filtered--phrase3

Boundary: http; state: filtered

```json
{
  "message": "this one",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "c9b868e3-0c98-45bb-bb91-c0a07ef74153",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "reference_type": "selected_property"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "event_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "7b0b2a12-8db7-462c-8765-f36941376a79",
      "message": "Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?",
      "requires_clarification": true
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "c9b868e3-0c98-45bb-bb91-c0a07ef74153",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "c9b868e3-0c98-45bb-bb91-c0a07ef74153",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "event_ids: expected ['P-1'], actual []"
  ]
}
```

## 19_references/second_index--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "2",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "fd42fdc0-3370-4652-8ca7-ae9ae7746c64",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "selected_index": 1
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "547c40a8-1f19-46e0-9610-c2d5d741b46d",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "fd42fdc0-3370-4652-8ca7-ae9ae7746c64",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-1",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": 1
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "fd42fdc0-3370-4652-8ca7-ae9ae7746c64",
        "property_id": "P-1",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "fd42fdc0-3370-4652-8ca7-ae9ae7746c64",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-1"
    ],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'property'; actual 'Ji, yeh option aap ko pasand aaya, note kar liya.'",
    "event_ids: expected empty, actual ['P-1']"
  ]
}
```

## 19_references/second_index--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "dusri",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "245f4267-9b87-4092-b13a-4b0abfd5754a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "selected_index": 1
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "4d0ecbc0-c4b8-48f7-a70b-c47a7f9e550f",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "245f4267-9b87-4092-b13a-4b0abfd5754a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-1",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": 1
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "245f4267-9b87-4092-b13a-4b0abfd5754a",
        "property_id": "P-1",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "245f4267-9b87-4092-b13a-4b0abfd5754a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-1"
    ],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'property'; actual 'Ji, yeh option aap ko pasand aaya, note kar liya.'",
    "event_ids: expected empty, actual ['P-1']"
  ]
}
```

## 19_references/second_index--filtered--phrase3

Boundary: http; state: filtered

```json
{
  "message": "second option",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9f8d6b0a-37e2-49f2-9e3d-28eb413040fb",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "selected_index": 1
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "f9f649c9-30b8-4e86-bc6a-04909291b144",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9f8d6b0a-37e2-49f2-9e3d-28eb413040fb",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-1",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": 1
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "9f8d6b0a-37e2-49f2-9e3d-28eb413040fb",
        "property_id": "P-1",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "9f8d6b0a-37e2-49f2-9e3d-28eb413040fb",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-1"
    ],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'property'; actual 'Ji, yeh option aap ko pasand aaya, note kar liya.'",
    "event_ids: expected empty, actual ['P-1']"
  ]
}
```

## 19_references/second_word--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "doosri wali",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "bd7d8626-55c4-4db6-80b0-c2485efbe7c6",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "reference_type": "second_result"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "4149e165-8830-43aa-b78a-9b77b7d98edc",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "bd7d8626-55c4-4db6-80b0-c2485efbe7c6",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-1",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "bd7d8626-55c4-4db6-80b0-c2485efbe7c6",
        "property_id": "P-1",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "bd7d8626-55c4-4db6-80b0-c2485efbe7c6",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-1"
    ],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'property'; actual 'Ji, yeh option aap ko pasand aaya, note kar liya.'",
    "event_ids: expected empty, actual ['P-1']"
  ]
}
```

## 19_references/second_word--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "second result",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "abb24859-c4aa-4fe2-ac15-c2e58d2aa056",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "reference_type": "second_result"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "614ba570-514a-4ea0-b521-4c8956a6a129",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "abb24859-c4aa-4fe2-ac15-c2e58d2aa056",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-1",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "abb24859-c4aa-4fe2-ac15-c2e58d2aa056",
        "property_id": "P-1",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "abb24859-c4aa-4fe2-ac15-c2e58d2aa056",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-1"
    ],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'property'; actual 'Ji, yeh option aap ko pasand aaya, note kar liya.'",
    "event_ids: expected empty, actual ['P-1']"
  ]
}
```

## 19_references/second_word--filtered--phrase3

Boundary: http; state: filtered

```json
{
  "message": "dusri property",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "bbc6fd30-5904-447f-9146-6e64b15897dc",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "unknown",
      "interaction_action": "liked",
      "reference_type": "second_result"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "event_ids"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "334a91dc-4779-4dfa-aef1-2bc98ca41e1d",
      "message": "Ji, yeh option aap ko pasand aaya, note kar liya.",
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "bbc6fd30-5904-447f-9146-6e64b15897dc",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-1",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "unknown",
          "interaction_action": "liked",
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "bbc6fd30-5904-447f-9146-6e64b15897dc",
        "property_id": "P-1",
        "action": "liked",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "bbc6fd30-5904-447f-9146-6e64b15897dc",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [
      "P-1"
    ],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'property'; actual 'Ji, yeh option aap ko pasand aaya, note kar liya.'",
    "event_ids: expected empty, actual ['P-1']"
  ]
}
```

## 20_cross_cutting/filtered_booking--filtered--phrase1

Boundary: http; state: filtered

```json
{
  "message": "pehli ki visit book kar dein",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "507d6544-4205-4722-9adb-774c877c6c7e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0,
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "booked_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "c98c39a5-5802-4452-a394-14456f3a8f29",
      "message": "Ji, appointment request confirm ho gayi. Appointments page par details dekh sakte hain.",
      "appointment": {
        "appointment_id": "84a1ef19-30f0-42bc-8fb8-844fe1b49171",
        "status": "confirmed"
      },
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "507d6544-4205-4722-9adb-774c877c6c7e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [
      [
        "POST",
        "/appointments",
        {
          "client_name": "Ali",
          "client_phone": "+923001234567",
          "client_email": "ali@example.com",
          "employee_name": "Sara AI Agent",
          "employee_email": "sara@realestatehub.pk",
          "property_id": "P-2",
          "property_name": "Home P-2",
          "starts_at": "2030-01-02T10:00:00+05:00",
          "duration_minutes": 60,
          "meeting_notes": ""
        }
      ]
    ],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "507d6544-4205-4722-9adb-774c877c6c7e",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": [
      "P-2"
    ]
  },
  "violations": [
    "booked_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 20_cross_cutting/filtered_booking--filtered--phrase2

Boundary: http; state: filtered

```json
{
  "message": "first option visit please",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "f36baf7e-0a63-4244-8a48-7339dcd2c02f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0,
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "booked_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "c1ce410f-a28c-455a-aa03-35fc2641221b",
      "message": "Ji, appointment request confirm ho gayi. Appointments page par details dekh sakte hain.",
      "appointment": {
        "appointment_id": "1c713308-7047-4f73-a689-a7ccf2bc3939",
        "status": "confirmed"
      },
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "f36baf7e-0a63-4244-8a48-7339dcd2c02f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [
      [
        "POST",
        "/appointments",
        {
          "client_name": "Ali",
          "client_phone": "+923001234567",
          "client_email": "ali@example.com",
          "employee_name": "Sara AI Agent",
          "employee_email": "sara@realestatehub.pk",
          "property_id": "P-2",
          "property_name": "Home P-2",
          "starts_at": "2030-01-02T10:00:00+05:00",
          "duration_minutes": 60,
          "meeting_notes": ""
        }
      ]
    ],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "f36baf7e-0a63-4244-8a48-7339dcd2c02f",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": [
      "P-2"
    ]
  },
  "violations": [
    "booked_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 20_cross_cutting/filtered_booking--filtered--phrase3

Boundary: http; state: filtered

```json
{
  "message": "option 1 visit karni hai",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "aea42931-990a-4985-ac65-8254640983ce",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0,
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "booked_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "e34df6ce-afaf-4abc-81c1-ca89af2bad96",
      "message": "Ji, appointment request confirm ho gayi. Appointments page par details dekh sakte hain.",
      "appointment": {
        "appointment_id": "6dbd647c-2a7b-4451-a4df-87c3c892d04c",
        "status": "confirmed"
      },
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "aea42931-990a-4985-ac65-8254640983ce",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [
      [
        "POST",
        "/appointments",
        {
          "client_name": "Ali",
          "client_phone": "+923001234567",
          "client_email": "ali@example.com",
          "employee_name": "Sara AI Agent",
          "employee_email": "sara@realestatehub.pk",
          "property_id": "P-2",
          "property_name": "Home P-2",
          "starts_at": "2030-01-02T10:00:00+05:00",
          "duration_minutes": 60,
          "meeting_notes": ""
        }
      ]
    ],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "aea42931-990a-4985-ac65-8254640983ce",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": [
      "P-2"
    ]
  },
  "violations": [
    "booked_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 20_cross_cutting/filtered_booking--filtered--phrase4

Boundary: http; state: filtered

```json
{
  "message": "pehli wali book karo",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "f867dfc0-3e47-4853-a1da-89025b99930a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0,
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "booked_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "7d4bf3b6-6da9-43f3-b40f-dba61afb0a0a",
      "message": "Ji, appointment request confirm ho gayi. Appointments page par details dekh sakte hain.",
      "appointment": {
        "appointment_id": "9ec720fa-6f1f-456d-9df3-35d3b3d0f97c",
        "status": "confirmed"
      },
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "f867dfc0-3e47-4853-a1da-89025b99930a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [
      [
        "POST",
        "/appointments",
        {
          "client_name": "Ali",
          "client_phone": "+923001234567",
          "client_email": "ali@example.com",
          "employee_name": "Sara AI Agent",
          "employee_email": "sara@realestatehub.pk",
          "property_id": "P-2",
          "property_name": "Home P-2",
          "starts_at": "2030-01-02T10:00:00+05:00",
          "duration_minutes": 60,
          "meeting_notes": ""
        }
      ]
    ],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "f867dfc0-3e47-4853-a1da-89025b99930a",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": [
      "P-2"
    ]
  },
  "violations": [
    "booked_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 20_cross_cutting/filtered_booking--filtered--phrase5

Boundary: http; state: filtered

```json
{
  "message": "schedule first property",
  "effective_context": {
    "saved_before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "1101155f-565b-4502-bb7b-f5c49a1908e1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit",
      "selected_index": 0,
      "starts_at": "2030-01-02T10:00:00+05:00"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "booked_ids": [
        "P-1"
      ]
    }
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "7f75bd44-8f3b-489c-9869-15bbe8011c9d",
      "message": "Ji, appointment request confirm ho gayi. Appointments page par details dekh sakte hain.",
      "appointment": {
        "appointment_id": "364e5f0d-4e62-4ebb-9c3a-53bd1c979cab",
        "status": "confirmed"
      },
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "1101155f-565b-4502-bb7b-f5c49a1908e1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": "P-2",
      "pending_action": null,
      "turn_count": 3,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "schedule_visit",
          "interaction_action": null,
          "selected_index": 0
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [
      [
        "POST",
        "/appointments",
        {
          "client_name": "Ali",
          "client_phone": "+923001234567",
          "client_email": "ali@example.com",
          "employee_name": "Sara AI Agent",
          "employee_email": "sara@realestatehub.pk",
          "property_id": "P-2",
          "property_name": "Home P-2",
          "starts_at": "2030-01-02T10:00:00+05:00",
          "duration_minutes": 60,
          "meeting_notes": ""
        }
      ]
    ],
    "searches": [
      {
        "city": "Lahore",
        "area": "DHA",
        "purpose": "purchase",
        "budget": 20000000,
        "property_type": "Apartment",
        "bedrooms": 3
      },
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "1101155f-565b-4502-bb7b-f5c49a1908e1",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 2,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        },
        {
          "intent": "property_details",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": [
      "P-2"
    ]
  },
  "violations": [
    "booked_ids: expected ['P-1'], actual ['P-2']"
  ]
}
```

## 20_cross_cutting/offtopic_booking--pending--phrase1

Boundary: http; state: pending

```json
{
  "message": "weather kaisa hai, khair visit book karni hai",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne Lahore mein 2 crore tak apartment purchase ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "38a5eeaf-9c5c-49b2-82e4-a9a509f826c1",
      "message": "Saved requirement continue karni hai ya koi preference change karni hai?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Saved requirement continue karni hai ya koi preference change karni hai?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne Lahore mein 2 crore tak apartment purchase ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Saved requirement continue karni hai ya koi preference change karni hai?'"
  ]
}
```

## 20_cross_cutting/offtopic_booking--pending--phrase2

Boundary: http; state: pending

```json
{
  "message": "are you a bot, anyway schedule visit",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne Lahore mein 2 crore tak apartment purchase ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "c70f1976-6cd8-4e70-a0ed-423cb7b3f1a2",
      "message": "Saved requirement continue karni hai ya koi preference change karni hai?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Saved requirement continue karni hai ya koi preference change karni hai?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne Lahore mein 2 crore tak apartment purchase ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Saved requirement continue karni hai ya koi preference change karni hai?'"
  ]
}
```

## 20_cross_cutting/offtopic_booking--pending--phrase3

Boundary: http; state: pending

```json
{
  "message": "match choro, visit karni hai",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne Lahore mein 2 crore tak apartment purchase ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "f2c97e7c-3ec5-4474-9a19-05b51cf040fe",
      "message": "Saved requirement continue karni hai ya koi preference change karni hai?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Saved requirement continue karni hai ya koi preference change karni hai?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne Lahore mein 2 crore tak apartment purchase ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Saved requirement continue karni hai ya koi preference change karni hai?'"
  ]
}
```

## 20_cross_cutting/offtopic_booking--pending--phrase4

Boundary: http; state: pending

```json
{
  "message": "job ka baad mein, visit please",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne Lahore mein 2 crore tak apartment purchase ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "9d6fb9a9-2887-43e9-b445-da3f6b4dc626",
      "message": "Saved requirement continue karni hai ya koi preference change karni hai?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Saved requirement continue karni hai ya koi preference change karni hai?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne Lahore mein 2 crore tak apartment purchase ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Saved requirement continue karni hai ya koi preference change karni hai?'"
  ]
}
```

## 20_cross_cutting/offtopic_booking--pending--phrase5

Boundary: http; state: pending

```json
{
  "message": "acha visit ka intezam kar dein",
  "effective_context": {
    "saved_before": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne Lahore mein 2 crore tak apartment purchase ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "schedule_visit"
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "property"
      ]
    },
    "empty": [
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "c99ce7bf-2a73-4140-aca7-3567fd703c5f",
      "message": "Saved requirement continue karni hai ya koi preference change karni hai?",
      "requires_clarification": true
    },
    "saved": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Saved requirement continue karni hai ya koi preference change karni hai?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [],
    "appointments": [],
    "searches": [],
    "before": {
      "pending_returning_confirm": true,
      "pending_returning_confirm_question": "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne Lahore mein 2 crore tak apartment purchase ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?",
      "returning_customer_handled": true,
      "turn_count": 1
    },
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.message: missing 'property'; actual 'Saved requirement continue karni hai ya koi preference change karni hai?'"
  ]
}
```

## 20_cross_cutting/phase_typo_booking--known--phrase1

Boundary: http; state: known

```json
{
  "message": "DHA mein dikhao, visit bhi karni hai",
  "effective_context": {
    "saved_before": {},
    "preferences_before": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "semantic_fixture": {
      "intent": "property_search",
      "required": {
        "area": "DHA"
      }
    }
  },
  "expected": {
    "eq": {
      "status": 200,
      "response.requires_clarification": true
    },
    "contains": {
      "response.message": [
        "DHA Phase 5",
        "DHA Phase 6"
      ]
    },
    "empty": [
      "appointments"
    ]
  },
  "actual": {
    "status": 200,
    "response": {
      "conversation_id": "6081461f-aea2-48cd-8240-c51ce6aced37",
      "message": "Theek hai! DHA Phase 5 mein ye verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.",
      "recommendation_session_id": "76573c7a-c65f-41f5-a992-6bc885c9d6ae",
      "properties": [
        {
          "property_id": "P-2",
          "property_name": "Home P-2",
          "city": "Lahore",
          "area": "DHA",
          "price": 12000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        },
        {
          "property_id": "P-1",
          "property_name": "Home P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "currency": "PKR",
          "bedrooms": 3,
          "bathrooms": 2,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true,
          "status": "Ready"
        }
      ],
      "requires_clarification": false
    },
    "saved": {
      "flexible": [],
      "excluded": {},
      "recommendation_session_id": "76573c7a-c65f-41f5-a992-6bc885c9d6ae",
      "property_order": [
        "P-2",
        "P-1"
      ],
      "selected": null,
      "pending_action": null,
      "turn_count": 1,
      "recent_turns": [
        {
          "intent": "property_search",
          "interaction_action": null,
          "selected_index": null
        }
      ]
    },
    "prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA Phase 5",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "events": [
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "76573c7a-c65f-41f5-a992-6bc885c9d6ae",
        "property_id": "P-2",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA Phase 5",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-2",
          "city": "Lahore",
          "area": "DHA",
          "price": 12000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      },
      {
        "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
        "conversation_id": "76573c7a-c65f-41f5-a992-6bc885c9d6ae",
        "property_id": "P-1",
        "action": "shown",
        "preference_snapshot": {
          "city": "Lahore",
          "area": "DHA Phase 5",
          "budget_min": null,
          "budget_max": 20000000,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ]
        },
        "property_snapshot": {
          "property_id": "P-1",
          "city": "Lahore",
          "area": "DHA",
          "price": 10000000.0,
          "bedrooms": 3,
          "property_type": "Apartment",
          "purpose": "purchase",
          "amenities": [
            "Parking"
          ],
          "available": true
        }
      }
    ],
    "appointments": [],
    "searches": [
      {
        "budget": 20000000,
        "city": "Lahore",
        "area": "DHA Phase 5",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "purchase",
        "amenities": [
          "Parking"
        ],
        "limit": 5
      }
    ],
    "before": {},
    "before_prefs": {
      "customer_id": "eec929e9-b7cb-43de-aae7-467509385617",
      "city": "Lahore",
      "area": "DHA",
      "budget_min": null,
      "budget_max": 20000000,
      "bedrooms": 3,
      "property_type": "Apartment",
      "purpose": "purchase",
      "amenities": [
        "Parking"
      ]
    },
    "pre_steps": [],
    "event_ids": [],
    "booked_ids": []
  },
  "violations": [
    "response.requires_clarification: expected True, actual False",
    "response.message: missing 'DHA Phase 6'; actual 'Theek hai! DHA Phase 5 mein ye verified options available hain: 1. Home P-2 — DHA, Lahore — 3 bedrooms — purchase — 12,000,000 PKR 2. Home P-1 — DHA, Lahore — 3 bedrooms — purchase — 10,000,000 PKR Filhaal yahi verified options available hain. In mein se kaunsa option aapko behtar lag raha hai — details dekhni hon ya visit schedule karni ho to batayein.'"
  ]
}
```
