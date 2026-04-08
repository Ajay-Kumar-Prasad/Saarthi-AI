"use client"

import { Fragment, useState } from "react"
import { Dialog, Disclosure, DisclosureButton, DisclosurePanel } from "@headlessui/react"
import { ChevronDown, Database } from "lucide-react"

type ProofOfLogic = {
  dataPoints?: string[]
  sqlQuery?: string
}

type ResponseCardProps = {
  summary: string
  proof?: ProofOfLogic
}

export default function ResponseCard({ summary, proof }: ResponseCardProps) {
  const [isSqlOpen, setIsSqlOpen] = useState(false)

  const dataPoints = proof?.dataPoints ?? []
  const sqlQuery = proof?.sqlQuery?.trim() || "-- SQL query unavailable"

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <p className="text-sm leading-relaxed text-gray-800 dark:text-gray-100">{summary}</p>

      <div className="mt-4">
        <Disclosure as="div" className="rounded-lg border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/40">
          {({ open }) => (
            <>
              <DisclosureButton className="flex w-full items-center justify-between px-3 py-2.5 text-left text-sm font-medium text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800">
                <span>Proof of Logic</span>
                <ChevronDown
                  className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
                  aria-hidden="true"
                />
              </DisclosureButton>

              <DisclosurePanel className="space-y-3 border-t border-gray-200 px-3 py-3 dark:border-gray-700">
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Data Points</p>
                  {dataPoints.length === 0 ? (
                    <p className="text-xs text-gray-500 dark:text-gray-400">No data points available.</p>
                  ) : (
                    <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700 dark:text-gray-200">
                      {dataPoints.map((point, idx) => (
                        <li key={`${point}-${idx}`}>{point}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => setIsSqlOpen(true)}
                  className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100 dark:border-indigo-800 dark:bg-indigo-950/30 dark:text-indigo-300 dark:hover:bg-indigo-950/50"
                >
                  <Database className="h-3.5 w-3.5" />
                  View SQL
                </button>
              </DisclosurePanel>
            </>
          )}
        </Disclosure>
      </div>

      <Dialog as={Fragment} open={isSqlOpen} onClose={setIsSqlOpen}>
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
          <Dialog.Panel className="relative z-10 w-full max-w-2xl rounded-xl border border-gray-200 bg-white p-4 shadow-xl dark:border-gray-700 dark:bg-gray-900">
            <Dialog.Title className="text-sm font-semibold text-gray-900 dark:text-white">SQL Query</Dialog.Title>
            <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-950">
              <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words text-xs leading-relaxed text-gray-800 dark:text-gray-200">
                {sqlQuery}
              </pre>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => setIsSqlOpen(false)}
                className="rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
              >
                Close
              </button>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
    </div>
  )
}

export type { ResponseCardProps, ProofOfLogic }
