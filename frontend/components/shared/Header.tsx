export default function Header({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="border-b border-gray-200 dark:border-gray-800 px-8 py-4 bg-white dark:bg-gray-950">
      <h1 className="text-gray-900 dark:text-white font-semibold text-xl">{title}</h1>
      {subtitle && <p className="text-gray-500 dark:text-gray-400 text-sm mt-0.5">{subtitle}</p>}
    </div>
  )
}
