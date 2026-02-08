"use client";

import {
  IconChevronDown,
  IconHome,
  IconMail,
  type Icon,
} from "@tabler/icons-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";
import * as Collapsible from "@radix-ui/react-collapsible";

export type NavMainItem = {
  title: string;
  url: string;
  icon?: Icon;
  children?: { title: string; url: string }[];
};

export function NavMain({ items }: { items: NavMainItem[] }) {
  const pathname = usePathname();

  return (
    <SidebarGroup>
      <SidebarGroupContent className="flex max-h-[50vh] min-w-0 flex-col gap-2 overflow-y-auto">
        <SidebarMenu>
          <SidebarMenuItem className="flex items-center gap-2">
            <SidebarMenuButton
              tooltip="Home"
              className="bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground active:bg-primary/90 min-w-8 duration-200 ease-linear"
              asChild
            >
              <Link href="/dashboard">
                <IconHome />
                <span>Home</span>
              </Link>
            </SidebarMenuButton>
            <Button
              size="icon"
              className="size-8 group-data-[collapsible=icon]:opacity-0"
              variant="outline"
            >
              <IconMail />
              <span className="sr-only">Inbox</span>
            </Button>
          </SidebarMenuItem>
        </SidebarMenu>
        <SidebarMenu>
          {items.map((item) => {
            const isAnalyticsParent = item.children != null;
            const isAnalyticsActive =
              isAnalyticsParent && pathname?.startsWith("/dashboard/analytics");

            if (isAnalyticsParent && item.children?.length) {
              return (
                <Collapsible.Root
                  key={item.title}
                  defaultOpen={isAnalyticsActive}
                  asChild
                >
                  <SidebarMenuItem className="group">
                    <Collapsible.Trigger asChild>
                      <SidebarMenuButton
                        tooltip={item.title}
                        isActive={isAnalyticsActive}
                        className="w-full"
                      >
                        {item.icon && <item.icon />}
                        <span>{item.title}</span>
                        <IconChevronDown className="ml-auto size-4 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                      </SidebarMenuButton>
                    </Collapsible.Trigger>
                    <Collapsible.Content>
                      <SidebarMenuSub>
                        {item.children.map((sub) => (
                          <SidebarMenuSubItem key={sub.url}>
                            <SidebarMenuSubButton
                              asChild
                              isActive={pathname === sub.url}
                            >
                              <Link href={sub.url}>{sub.title}</Link>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        ))}
                      </SidebarMenuSub>
                    </Collapsible.Content>
                  </SidebarMenuItem>
                </Collapsible.Root>
              );
            }

            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton
                  tooltip={item.title}
                  asChild
                  isActive={pathname === item.url}
                >
                  <Link href={item.url}>
                    {item.icon && <item.icon />}
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
