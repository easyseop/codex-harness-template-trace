# Technical Requirements Document — CDC Data Pipeline

## Layer Design

### Data Layer
- Raw CDC storage receives source change events.
- CDC sequence order is preserved before transformation.

### Logic Layer
- Quality validation runs before serving mart generation.

### Presentation Layer
- Pipeline status is exposed to operators.
