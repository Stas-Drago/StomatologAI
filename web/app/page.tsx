import Link from "next/link";
import { ArrowRight, MapPin, ShieldCheck, Sparkles } from "lucide-react";
import { SiteFooter, SiteHeader } from "@/components/site-shell";
import { articles } from "@/lib/articles";

const steps = [
  ["01", "Загрузите фото", "Выберите чёткое фото зубов при хорошем освещении."],
  ["02", "Получите оценку", "Алгоритм покажет, что он распознал, и объяснит результат простым языком."],
  ["03", "Выберите следующий шаг", "Найдите стоматологию рядом, если очная консультация нужна уже сейчас."],
];

export default function Home() {
  return <main><SiteHeader />
    <section className="hero"><div className="hero-copy"><p className="eyebrow"><Sparkles size={16} /> Предварительная оценка с ИИ</p><h1>Поймите, что происходит с зубами, до визита в клинику.</h1><p className="lead">Загрузите фотографию улыбки, получите понятную предварительную оценку и найдите стоматологию рядом.</p><div className="hero-actions"><Link className="button button-primary" href="/scan">Проверить фото <ArrowRight size={18} /></Link><Link className="button button-text" href="/clinics">Найти клинику</Link></div><p className="privacy-note"><ShieldCheck size={16} /> Фото удаляется сразу после анализа и не используется для обучения.</p></div><div className="hero-visual" aria-label="Предварительный анализ улыбки"><div className="scan-card"><div className="scan-card-top"><span>DentalHelper Scan</span><span className="live-dot">Анализ</span></div><div className="scan-smile">⌣</div><div className="scan-line" /><div className="scan-result"><span>Предварительная оценка</span><strong>Проверьте улыбку</strong><small>Ответ за несколько секунд</small></div></div><div className="floating-stat"><span>1</span><p>Фото<br /><b>без сохранения</b></p></div></div></section>
    <section className="section process"><div className="section-heading"><p className="eyebrow">Как это работает</p><h2>Три спокойных шага к ясности</h2></div><div className="steps">{steps.map(([number, title, text]) => <article className="step" key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p></article>)}</div></section>
    <section className="feature-band"><div><p className="eyebrow">Рядом с вами</p><h2>Не откладывайте очный осмотр.</h2><p>Укажите адрес или точку на карте. Мы покажем семь стоматологий поблизости и расстояние до каждой.</p><Link className="button button-light" href="/clinics">Открыть карту <MapPin size={18} /></Link></div><div className="map-preview" aria-hidden="true"><i /><i /><i /><b><MapPin size={18} /> 7 клиник рядом</b></div></section>
    <section className="section articles-preview"><div className="section-heading row-heading"><div><p className="eyebrow">Полезное чтение</p><h2>Забота, которую легко встроить в день</h2></div><Link href="/articles" className="text-link">Все статьи <ArrowRight size={17} /></Link></div><div className="article-grid">{articles.slice(0, 3).map((article) => <Link href={`/articles/${article.slug}`} className="article-card" key={article.slug}><img src={article.image} alt="" /><div><p>{article.tag}</p><h3>{article.title}</h3><span>Читать <ArrowRight size={16} /></span></div></Link>)}</div></section><SiteFooter /></main>;
}
