import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { notFound } from "next/navigation";
import { SiteFooter, SiteHeader } from "@/components/site-shell";
import { articleBySlug, articles } from "@/lib/articles";
export function generateStaticParams() { return articles.map(({ slug }) => ({ slug })); }
export default async function ArticlePage({ params }: { params: Promise<{ slug: string }> }) { const { slug } = await params; const article = articleBySlug(slug); if (!article) notFound(); return <main><SiteHeader /><article className="article-page"><Link className="back-link" href="/articles"><ArrowLeft size={17} /> Все статьи</Link><p className="eyebrow">{article.tag}</p><h1>{article.title}</h1><p className="article-summary">{article.summary}</p><img className="article-cover" src={article.image} alt="" /><div className="article-content"><div>{article.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}<p>Информация в статье носит общий характер и не заменяет консультацию специалиста.</p></div><aside><p>Коротко</p><ul>{article.tips.map((tip) => <li key={tip}>{tip}</li>)}</ul></aside></div><Link className="next-article" href="/articles">Другие рекомендации <ArrowRight size={18} /></Link></article><SiteFooter /></main>; }
