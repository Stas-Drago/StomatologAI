import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { SiteFooter, SiteHeader } from "@/components/site-shell";
import { articles } from "@/lib/articles";
export default function ArticlesPage() { return <main><SiteHeader /><section className="page-intro"><p className="eyebrow">Рекомендации по уходу</p><h1>Полезные привычки для здоровья зубов</h1><p>Короткие материалы о том, как поддерживать улыбку между визитами к специалисту.</p></section><section className="section full-article-grid">{articles.map((article) => <Link href={`/articles/${article.slug}`} className="article-card" key={article.slug}><img src={article.image} alt="" /><div><p>{article.tag}</p><h2>{article.title}</h2><span>{article.summary}</span><b>Читать статью <ArrowRight size={16} /></b></div></Link>)}</section><SiteFooter /></main>; }
