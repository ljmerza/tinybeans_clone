# Tabs Component

A flexible tabs component built with Radix UI that allows you to organize content into different sections.

## Installation

The tabs component uses `@radix-ui/react-tabs` which is already installed in this project.

## Usage

### Basic Example

```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function Example() {
  return (
    <Tabs defaultValue="account" className="w-[400px]">
      <TabsList>
        <TabsTrigger value="account">Account</TabsTrigger>
        <TabsTrigger value="password">Password</TabsTrigger>
      </TabsList>
      <TabsContent value="account">
        Make changes to your account here.
      </TabsContent>
      <TabsContent value="password">
        Change your password here.
      </TabsContent>
    </Tabs>
  );
}
```

### With Custom Content

```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function TabsDemo() {
  return (
    <Tabs defaultValue="overview" className="w-full">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="analytics">Analytics</TabsTrigger>
        <TabsTrigger value="reports">Reports</TabsTrigger>
      </TabsList>
      <TabsContent value="overview" className="space-y-4">
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">Overview Content</h3>
          <p className="text-sm text-muted-foreground">
            Your overview information goes here.
          </p>
        </div>
      </TabsContent>
      <TabsContent value="analytics" className="space-y-4">
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">Analytics Content</h3>
          <p className="text-sm text-muted-foreground">
            Your analytics data goes here.
          </p>
        </div>
      </TabsContent>
      <TabsContent value="reports" className="space-y-4">
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">Reports Content</h3>
          <p className="text-sm text-muted-foreground">
            Your reports go here.
          </p>
        </div>
      </TabsContent>
    </Tabs>
  );
}
```

### Controlled Tabs

```tsx
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function ControlledExample() {
  const [activeTab, setActiveTab] = useState("tab1");

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab}>
      <TabsList>
        <TabsTrigger value="tab1">Tab 1</TabsTrigger>
        <TabsTrigger value="tab2">Tab 2</TabsTrigger>
        <TabsTrigger value="tab3">Tab 3</TabsTrigger>
      </TabsList>
      <TabsContent value="tab1">Content for Tab 1</TabsContent>
      <TabsContent value="tab2">Content for Tab 2</TabsContent>
      <TabsContent value="tab3">Content for Tab 3</TabsContent>
    </Tabs>
  );
}
```

## API Reference

### Tabs

The root component that manages the state of the tabs.

**Props:**
- `defaultValue?: string` - The value of the tab that should be active by default
- `value?: string` - The controlled value of the tab to activate
- `onValueChange?: (value: string) => void` - Event handler called when the value changes
- `orientation?: "horizontal" | "vertical"` - The orientation of the tabs
- `dir?: "ltr" | "rtl"` - The reading direction
- `activationMode?: "automatic" | "manual"` - Whether tabs are activated automatically on focus or manually

### TabsList

The container for the tab triggers.

**Props:**
- `className?: string` - Additional CSS classes
- All standard div props

### TabsTrigger

The button that activates a tab panel.

**Props:**
- `value: string` - The value of the tab to activate (required)
- `disabled?: boolean` - Whether the tab is disabled
- `className?: string` - Additional CSS classes
- All standard button props

### TabsContent

The panel that contains the content for a tab.

**Props:**
- `value: string` - The value of the tab this content is for (required)
- `forceMount?: boolean` - Whether to force mount the content
- `className?: string` - Additional CSS classes
- All standard div props

## Styling

The component uses Tailwind CSS classes and follows the design system's color scheme. You can customize the appearance by passing `className` props to any of the components.

## Accessibility

Built on Radix UI, this component follows the [WAI-ARIA Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/):
- Uses proper ARIA roles and attributes
- Supports keyboard navigation (Arrow keys, Home, End, Tab)
- Manages focus appropriately
- Supports both automatic and manual activation modes
