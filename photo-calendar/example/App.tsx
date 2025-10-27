import { PhotoCalendar, type PhotoEntry } from '@tinybeans/photo-calendar';

// Generate sample photo entries for demonstration
// Using various image sizes to show object-fit: cover working properly
const generateSampleEntries = (): PhotoEntry[] => {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();

  // Add photos for various days in the current month with different aspect ratios
  const photoDays = [1, 3, 5, 7, 9, 12, 14, 16, 18, 20, 22, 25, 27, 28];
  const imageSizes = [
    { width: 400, height: 600 }, // Portrait
    { width: 800, height: 600 }, // Landscape
    { width: 500, height: 500 }, // Square
    { width: 1200, height: 800 }, // Wide landscape
    { width: 600, height: 900 }, // Tall portrait
    { width: 1000, height: 1000 }, // Large square
  ];

  return photoDays.map((day, index) => {
    const date = new Date(Date.UTC(year, month, day, 12, 0, 0));
    const size = imageSizes[index % imageSizes.length];
    const seed = `${year}-${month}-${day}`;

    return {
      datetime: date.toISOString(),
      photos: [
        `https://picsum.photos/seed/${seed}/${size.width}/${size.height}`,
        // Could add more photos here for multi-photo entries
      ]
    };
  });
};

export function App() {
  const sampleEntries = generateSampleEntries();

  return (
    <main>
      <h1>Photo Calendar Library Playground</h1>
      <p>
        This example consumes the library entry point directly so you can iterate on the primitives while
        keeping build and runtime behaviour aligned with downstream apps.
      </p>
      <PhotoCalendar entries={sampleEntries} />
    </main>
  );
}
