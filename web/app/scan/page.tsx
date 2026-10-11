import { ScanLine } from "lucide-react";
import { SiteFooter, SiteHeader } from "@/components/site-shell";
import { ScanWorkbench } from "@/components/scan-workbench";
export default function ScanPage() { return <main><SiteHeader /><section className="page-intro"><p className="eyebrow"><ScanLine size={16} /> Проверка по фотографии</p><h1>Загрузите снимок. Получите ориентир.</h1><p>Для лучшего результата используйте чёткое фото при дневном или ровном искусственном освещении.</p></section><section className="section scan-section"><ScanWorkbench /></section><SiteFooter /></main>; }
