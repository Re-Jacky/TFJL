# UI Feature Modules

Each subdirectory = one feature tab. Exports via `index.ts`.

## Structure

```
content/
├── collaboration/   # Script editor for collab mode
├── automator/       # Auto-battle configuration
├── shortcut/        # Hotkey bindings
├── level-monitoring/ # Level monitoring and detection
├── custom-operations/ # Custom operations configuration
├── components/      # Shared UI components
└── index.ts         # Re-exports all features
```

## Adding a Feature

1. Create `featureName/` directory
2. Add `Content.tsx` as main component
3. Add `index.ts` exporting Content
4. Register in parent `index.ts`
5. Add tab in `../tabs/TaskTabs.tsx`

## Component Pattern

```typescript
import React from 'react';
import { useAppSelector, useAppDispatch } from '@src/store/store';

const Content: React.FC = () => {
  const dispatch = useAppDispatch();
  const state = useAppSelector(selectState);
  
  return (/* JSX */);
};

export default Content;
```

## Naming

- Main component: `Content.tsx`
- Sub-components: PascalCase in same dir
- Styles: `styles.module.scss` (if needed)

## State Management

- Use `@src/store/slices/` for feature state
- Use `@src/store/thunks/` for async actions
- Selectors in `@src/store/selectors.ts`
