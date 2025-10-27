import { PhotoCalendar } from '@tinybeans/photo-calendar';

export function App() {
  return (
    <main>
      <h1>Photo Calendar Library Playground</h1>
      <p>
        This example consumes the library entry point directly so you can iterate on the primitives while
        keeping build and runtime behaviour aligned with downstream apps.
      </p>
      <PhotoCalendar />
    </main>
  );
}
