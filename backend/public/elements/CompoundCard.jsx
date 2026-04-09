import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { FlaskConical, Weight, Droplets, Layers, ExternalLink, Atom, Search } from "lucide-react"

function formatFormula(formula) {
  if (!formula) return "—"
  return formula.split("").map((ch, index) => {
    if (/\d/.test(ch)) return <sub key={index}>{ch}</sub>
    return <span key={index}>{ch}</span>
  })
}

function PropertyItem({ icon, label, value, unit }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border px-3 py-2" style={{ borderColor: "hsl(var(--border))", background: "color-mix(in srgb, hsl(var(--secondary)) 72%, transparent)" }}>
      <div className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ background: "color-mix(in srgb, hsl(var(--primary)) 16%, transparent)" }}>
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-[0.18em]" style={{ color: "hsl(var(--muted-foreground))" }}>{label}</div>
        <div className="truncate text-sm font-medium" style={{ color: "hsl(var(--foreground))" }}>
          {value}{unit ? <span className="ml-1 text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>{unit}</span> : null}
        </div>
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <Card className="w-full max-w-3xl overflow-hidden border-0" style={{ background: "linear-gradient(145deg, hsl(var(--card)) 0%, color-mix(in srgb, hsl(var(--card)) 86%, black) 100%)", color: "hsl(var(--card-foreground))" }}>
      <CardHeader className="space-y-3">
        <div className="flex items-center gap-2 text-sm" style={{ color: "hsl(var(--primary))" }}>
          <Search className="h-4 w-4" />
          <span>PubChem search in progress</span>
        </div>
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-full max-w-xl" />
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 md:grid-cols-[132px_1fr]">
          <div className="rounded-2xl border bg-white p-3" style={{ borderColor: "hsl(var(--border))" }}>
            <Skeleton className="h-20 w-full" />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
          </div>
        </div>
        <div className="text-sm" style={{ color: "hsl(var(--muted-foreground))" }}>
          {props.status || "Ищу подходящие соединения и собираю их свойства..."}
        </div>
      </CardContent>
    </Card>
  )
}

export default function CompoundCard() {
  if (props.loading) {
    return <LoadingState />
  }

  const name = props.name || "Unknown compound"
  const iupac = props.iupac_name || null
  const imageUrl = props.image_url || null
  const pubchemUrl = props.pubchem_url || null
  const whyItMatches = props.why_it_matches || null
  const synonyms = Array.isArray(props.synonyms) ? props.synonyms : []

  return (
    <Card className="w-full max-w-3xl overflow-hidden border-0" style={{ background: "linear-gradient(145deg, hsl(var(--card)) 0%, color-mix(in srgb, hsl(var(--card)) 86%, black) 100%)", color: "hsl(var(--card-foreground))", boxShadow: "0 16px 40px rgba(2, 8, 23, 0.22)" }}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <CardTitle className="truncate text-xl font-semibold">{name}</CardTitle>
            {iupac ? <div className="mt-1 text-sm italic" style={{ color: "hsl(var(--muted-foreground))" }}>{iupac}</div> : null}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {props.cid ? <Badge variant="outline" className="border-0 font-mono" style={{ background: "color-mix(in srgb, hsl(var(--primary)) 14%, transparent)", color: "hsl(var(--primary))" }}>CID {props.cid}</Badge> : null}
            {pubchemUrl ? (
              <a href={pubchemUrl} target="_blank" rel="noreferrer" className="flex h-8 w-8 items-center justify-center rounded-lg border transition-colors" style={{ borderColor: "hsl(var(--border))", color: "hsl(var(--primary))" }}>
                <ExternalLink className="h-4 w-4" />
              </a>
            ) : null}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-0">
        <div className="grid gap-4 md:grid-cols-[150px_1fr]">
          {imageUrl ? (
            <div className="flex items-start">
              <div className="flex h-[112px] w-[150px] items-center justify-center rounded-2xl border bg-white p-3" style={{ borderColor: "hsl(var(--border))" }}>
                <img src={imageUrl} alt={`${name} structure`} className="max-h-full max-w-full object-contain" />
              </div>
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2">
            <PropertyItem icon={<FlaskConical className="h-4 w-4" style={{ color: "hsl(var(--primary))" }} />} label="Formula" value={<span className="font-mono text-xs">{formatFormula(props.molecular_formula)}</span>} />
            <PropertyItem icon={<Weight className="h-4 w-4" style={{ color: "hsl(var(--primary))" }} />} label="Mol. Weight" value={props.molecular_weight || "—"} unit="g/mol" />
            {props.xlogp != null ? <PropertyItem icon={<Droplets className="h-4 w-4" style={{ color: "hsl(var(--primary))" }} />} label="XLogP" value={props.xlogp} /> : null}
            {props.complexity != null ? <PropertyItem icon={<Layers className="h-4 w-4" style={{ color: "hsl(var(--primary))" }} />} label="Complexity" value={props.complexity} /> : null}
          </div>
        </div>

        {(props.hbond_donor_count != null || props.hbond_acceptor_count != null || props.tpsa != null) ? (
          <>
            <Separator />
            <div className="grid gap-3 sm:grid-cols-3">
              {props.hbond_donor_count != null ? (
                <PropertyItem icon={<Atom className="h-4 w-4" style={{ color: "hsl(var(--primary))" }} />} label="H-Donors" value={props.hbond_donor_count} />
              ) : null}
              {props.hbond_acceptor_count != null ? (
                <PropertyItem icon={<Atom className="h-4 w-4" style={{ color: "hsl(var(--primary))" }} />} label="H-Acceptors" value={props.hbond_acceptor_count} />
              ) : null}
              {props.tpsa != null ? (
                <PropertyItem icon={<Atom className="h-4 w-4" style={{ color: "hsl(var(--primary))" }} />} label="TPSA" value={props.tpsa} unit="Å²" />
              ) : null}
            </div>
          </>
        ) : null}

        {whyItMatches ? (
          <>
            <Separator />
            <div className="rounded-2xl border px-4 py-3 text-sm leading-relaxed" style={{ borderColor: "hsl(var(--border))", background: "color-mix(in srgb, hsl(var(--primary)) 10%, transparent)" }}>
              <div className="mb-1 text-[11px] uppercase tracking-[0.16em]" style={{ color: "hsl(var(--primary))" }}>Why it matches</div>
              <div style={{ color: "hsl(var(--foreground))" }}>{whyItMatches}</div>
            </div>
          </>
        ) : null}

        {synonyms.length > 0 ? (
          <>
            <Separator />
            <div className="flex flex-wrap gap-2">
              {synonyms.slice(0, 6).map((synonym, index) => (
                <Badge key={index} variant="outline" className="border-0 text-xs" style={{ background: "color-mix(in srgb, hsl(var(--muted)) 92%, transparent)", color: "hsl(var(--muted-foreground))" }}>
                  {synonym}
                </Badge>
              ))}
            </div>
          </>
        ) : null}

        {props.canonical_smiles ? (
          <>
            <Separator />
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="cursor-default truncate rounded-xl border px-3 py-2 font-mono text-xs" style={{ borderColor: "hsl(var(--border))", background: "color-mix(in srgb, hsl(var(--secondary)) 80%, transparent)", color: "hsl(var(--muted-foreground))" }}>
                    {props.canonical_smiles}
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top">
                  Canonical SMILES
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}
