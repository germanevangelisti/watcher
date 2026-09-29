import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

/**
 * Render de Markdown para las burbujas del chat.
 *
 * El modelo contesta en Markdown (`**negrita**`, listas, citas `>`), pero la
 * burbuja pintaba el string plano: el usuario veía los asteriscos y los `>`
 * literales en pantalla. Esto los renderiza, con el subconjunto que el modelo
 * realmente emite —no hace falta un parser completo ni una dependencia nueva.
 *
 * Reglas duras:
 *
 * - **Nunca `dangerouslySetInnerHTML`.** Se arman nodos de React, así que
 *   cualquier HTML que venga en el texto se escapa solo. La respuesta del agente
 *   es contenido no confiable y no debe poder inyectar marcado.
 * - **`_` no es cursiva.** Los montos del BO salen de campos como
 *   `monto_vigente_total`; interpretar el guión bajo partiría identificadores a
 *   la mitad. Solo `**negrita**`, `__negrita__`, `*cursiva*` y `` `código` ``.
 * - **Encabezados → texto en negrita**, no `<h1>`: un título gigante adentro de
 *   una burbuja de chat rompe la lectura y el ancho es de 80%.
 * - **Sin anidado.** `*cursiva **con negrita** adentro*` no se soporta; el modelo
 *   no lo emite y adivinarlo es más riesgo que beneficio.
 */

type Block =
  | { kind: "p"; text: string }
  | { kind: "ul"; items: string[] }
  | { kind: "ol"; items: string[] }
  | { kind: "quote"; blocks: Block[] }
  | { kind: "heading"; text: string }
  | { kind: "hr" }

const UL = /^[-*+•]\s+(.*)$/
const OL = /^\d{1,3}[.)]\s+(.*)$/
const HEADING = /^#{1,6}\s+(.*)$/
const QUOTE = /^>\s?(.*)$/
const HR = /^(?:-{3,}|\*{3,}|_{3,})$/

// Alternation en orden de especificidad: `**` antes que `*`, para que la negrita
// no se coma un asterisco y deje el otro colgado.
const INLINE = /(\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|`[^`\n]+`)/g

/** Parte el texto en bloques: párrafos, listas, citas, encabezados y reglas. */
function parseBlocks(lines: string[], depth = 0): Block[] {
  const blocks: Block[] = []
  let paragraph: string[] = []
  let list: { ordered: boolean; items: string[] } | null = null

  const flush = () => {
    if (paragraph.length) {
      blocks.push({ kind: "p", text: paragraph.join(" ") })
      paragraph = []
    }
    if (list) {
      blocks.push(
        list.ordered
          ? { kind: "ol", items: list.items }
          : { kind: "ul", items: list.items },
      )
      list = null
    }
  }

  let i = 0
  while (i < lines.length) {
    const line = lines[i].trim()

    if (!line) {
      flush()
      i++
      continue
    }

    if (HR.test(line)) {
      flush()
      blocks.push({ kind: "hr" })
      i++
      continue
    }

    const heading = line.match(HEADING)
    if (heading) {
      flush()
      blocks.push({ kind: "heading", text: heading[1] })
      i++
      continue
    }

    if (QUOTE.test(line)) {
      flush()
      const inner: string[] = []
      while (i < lines.length && QUOTE.test(lines[i].trim())) {
        inner.push(lines[i].trim().replace(QUOTE, "$1"))
        i++
      }
      // Una sola capa de cita: adentro, `>` vuelve a ser texto plano.
      blocks.push({
        kind: "quote",
        blocks:
          depth === 0
            ? parseBlocks(inner, depth + 1)
            : [{ kind: "p", text: inner.join(" ") }],
      })
      continue
    }

    const ul = line.match(UL)
    const ol = ul ? null : line.match(OL)
    if (ul || ol) {
      if (paragraph.length) {
        blocks.push({ kind: "p", text: paragraph.join(" ") })
        paragraph = []
      }
      const ordered = Boolean(ol)
      // Cambiar de viñeta a numeración corta la lista y abre otra.
      if (!list || list.ordered !== ordered) {
        flush()
        list = { ordered, items: [] }
      }
      list.items.push((ul ? ul[1] : ol![1]).trim())
      i++
      continue
    }

    paragraph.push(line)
    i++
  }

  flush()
  return blocks
}

/** Aplica el marcado inline (`**`, `*`, `` ` ``) devolviendo nodos de React. */
function renderInline(text: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  let key = 0

  for (const match of text.matchAll(INLINE)) {
    const token = match[0]
    const at = match.index ?? 0
    if (at > last) out.push(text.slice(last, at))

    if (token.startsWith("**") || token.startsWith("__")) {
      out.push(
        <strong key={key++} className="font-semibold">
          {token.slice(2, -2)}
        </strong>,
      )
    } else if (token.startsWith("`")) {
      out.push(
        <code
          key={key++}
          className="rounded bg-background/60 px-1 py-0.5 font-mono text-[0.85em]"
        >
          {token.slice(1, -1)}
        </code>,
      )
    } else {
      out.push(<em key={key++}>{token.slice(1, -1)}</em>)
    }
    last = at + token.length
  }

  if (last < text.length) out.push(text.slice(last))
  return out
}

function renderBlock(block: Block, key: number): ReactNode {
  switch (block.kind) {
    case "p":
      return <p key={key}>{renderInline(block.text)}</p>
    case "heading":
      return (
        <p key={key} className="font-semibold">
          {renderInline(block.text)}
        </p>
      )
    case "ul":
      return (
        <ul key={key} className="list-disc space-y-1 pl-5">
          {block.items.map((item, j) => (
            <li key={j}>{renderInline(item)}</li>
          ))}
        </ul>
      )
    case "ol":
      return (
        <ol key={key} className="list-decimal space-y-1 pl-5">
          {block.items.map((item, j) => (
            <li key={j}>{renderInline(item)}</li>
          ))}
        </ol>
      )
    case "quote":
      return (
        <blockquote
          key={key}
          className="space-y-2 border-l-2 border-current/30 pl-3 opacity-90"
        >
          {block.blocks.map(renderBlock)}
        </blockquote>
      )
    case "hr":
      return <hr key={key} className="border-current/20" />
  }
}

export function ChatMarkdown({
  content,
  className,
}: {
  content: string
  className?: string
}) {
  return (
    <div className={cn("space-y-2 text-sm leading-relaxed break-words", className)}>
      {parseBlocks(content.split("\n")).map(renderBlock)}
    </div>
  )
}
