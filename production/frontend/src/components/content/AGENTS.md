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

## Screenshot Folder Feature

New sub-components in `screenshot/components/`:

- `ImageBrowser.tsx` - Dropdown + prev/next navigation for screenshot files
- `CropEditor.tsx` - Interactive draggable/resizable boxes for manual cropping
- `CropLabeler.tsx` - Batch labeling UI for extracted crops

**Workflow:**
1. Browse screenshots from folder (dropdown or arrows)
2. Click "开始标注" → enter crop mode with 3 draggable boxes
3. Adjust boxes to fit actual card positions
4. Click "完成裁切" → extract 3 crops
5. Select card name for each crop → save labels → triggers training

**State Management:**
Local component state only (no Redux) - workflow is transient UI state.

**Keyboard Navigation:**
Arrow keys (Left/Right) navigate screenshots in browse mode only.
