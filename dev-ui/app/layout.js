import "./globals.css";

export const metadata = {
  title: "dev-ui - Slotta dummy frontend",
  icons: { icon: "data:," },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
