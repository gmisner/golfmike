export default function Footer() {
  return (
    <footer className="border-t border-border py-4 text-center text-xs text-muted-foreground">
      GolfMike &copy; {new Date().getFullYear()} &mdash; SWIM data via FAA
    </footer>
  )
}
