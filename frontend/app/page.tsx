"use client";
import Link from "next/link";
import { BookOpen, Users, Lightbulb, BarChart3 } from "lucide-react";

const features = [
  {
    icon: BookOpen,
    title: "Content Analysis",
    desc: "Extracts your main claim, contributions, and narrative structure.",
  },
  {
    icon: Users,
    title: "Audience Personas",
    desc: "Four simulated audience members react — novice to expert.",
  },
  {
    icon: Lightbulb,
    title: "Narrative & Clarity Coaching",
    desc: "Identifies story arc weaknesses and jargon-heavy passages.",
  },
  {
    icon: BarChart3,
    title: "Prioritized Revision Plan",
    desc: "Issues ranked High / Medium / Low with a revised opening.",
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col">
      {/* Hero */}
      <section className="flex flex-col items-center justify-center flex-1 px-6 py-24 text-center bg-gradient-to-b from-brand-50 to-white">
        <span className="text-xs font-semibold tracking-widest uppercase text-brand-600 mb-4">
          IEOR 4576 · Project 3
        </span>
        <h1 className="text-5xl font-bold text-slate-900 mb-4 leading-tight">
          StoryCoach
        </h1>
        <p className="text-xl text-slate-600 max-w-xl mb-10">
          Paste your talk outline, paper abstract, or slide text — and get
          structured feedback from six specialized AI agents in under 90 seconds.
        </p>
        <Link
          href="/analyze"
          className="bg-brand-600 hover:bg-brand-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors text-lg"
        >
          Analyze My Document →
        </Link>
      </section>

      {/* Features */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-4xl mx-auto grid grid-cols-1 sm:grid-cols-2 gap-8">
          {features.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="flex gap-4 items-start p-6 rounded-xl border border-slate-100 shadow-sm">
              <div className="bg-brand-100 p-3 rounded-lg">
                <Icon className="text-brand-600" size={22} />
              </div>
              <div>
                <h3 className="font-semibold text-slate-800 mb-1">{title}</h3>
                <p className="text-slate-500 text-sm">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer className="py-6 text-center text-slate-400 text-sm border-t border-slate-100">
        StoryCoach · Powered by Gemini 2.5 Pro + LangGraph
      </footer>
    </main>
  );
}
