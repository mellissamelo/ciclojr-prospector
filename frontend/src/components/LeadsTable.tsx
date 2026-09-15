import { StatusBadge } from "@/components/StatusBadge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { LeadRow } from "@/lib/types"

export function LeadsTable({ leads, showData = false }: { leads: LeadRow[]; showData?: boolean }) {
  if (leads.length === 0) {
    return <p className="text-sm text-muted-foreground">Nenhum lead aqui.</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nome</TableHead>
            <TableHead>CNPJ</TableHead>
            <TableHead>Bairro</TableHead>
            {showData && <TableHead>Data</TableHead>}
            <TableHead>Dono/Sócio</TableHead>
            <TableHead>Instagram</TableHead>
            <TableHead>Licenças pendentes</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {leads.map((l) => (
            <TableRow key={l.cnpj}>
              <TableCell className="max-w-64 truncate font-medium" title={l.nome}>{l.nome}</TableCell>
              <TableCell className="whitespace-nowrap tabular-nums text-muted-foreground">{l.cnpj}</TableCell>
              <TableCell className="whitespace-nowrap">{l.bairro || <span className="text-muted-foreground">—</span>}</TableCell>
              {showData && (
                <TableCell className="whitespace-nowrap text-muted-foreground">{l.data || "—"}</TableCell>
              )}
              <TableCell>{l.dono || <span className="text-muted-foreground">—</span>}</TableCell>
              <TableCell>
                {l.instagram ? (
                  <a
                    href={`https://instagram.com/${l.instagram}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary hover:underline"
                  >
                    @{l.instagram}
                  </a>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1.5">
                  {l.pendentes.map((p) => (
                    <StatusBadge key={p.sigla} license={p} />
                  ))}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
