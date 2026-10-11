import { MapPinned } from "lucide-react";
import { SiteFooter, SiteHeader } from "@/components/site-shell";
import { ClinicFinder } from "@/components/clinic-finder";
export default function ClinicsPage() { return <main><SiteHeader /><section className="page-intro compact"><p className="eyebrow"><MapPinned size={16} /> Стоматологии рядом</p><h1>Найдите клинику в удобном районе</h1><p>Введите адрес, используйте геолокацию или выберите место на карте.</p></section><section className="map-section"><ClinicFinder /></section><SiteFooter /></main>; }
